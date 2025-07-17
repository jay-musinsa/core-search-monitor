"""
이미지 저장소 및 메타데이터 관리 서비스
스크린샷 이미지의 저장, 관리, 최적화를 담당
"""

import os
import logging
import hashlib
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
import aiofiles
import boto3
from botocore.exceptions import ClientError

from app.core.database import get_database_client
from app.core.redis_client import get_redis_client


logger = logging.getLogger(__name__)


class ImageStorage:
    """이미지 저장소 관리 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_default_config()
        self.db_client = get_database_client()
        self.redis_client = get_redis_client()
        
        # 로컬 저장소 경로
        self.local_storage_path = Path(self.config.get("local_storage_path", "app/screenshots"))
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        
        # AWS S3 클라이언트 (선택적)
        self.s3_client = None
        if self.config.get("use_s3", False):
            self._initialize_s3_client()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """기본 설정 로드"""
        return {
            "local_storage_path": "app/screenshots",
            "use_s3": False,
            "s3_bucket": os.getenv("AWS_S3_BUCKET", ""),
            "s3_region": os.getenv("AWS_REGION", "ap-northeast-2"),
            "image_quality": 85,
            "max_image_size": 2048,
            "supported_formats": ["PNG", "JPEG", "WEBP"],
            "retention_days": 90,
            "enable_compression": True,
            "enable_thumbnail": True,
            "thumbnail_size": (300, 200),
            "cache_ttl": 3600
        }
    
    def _initialize_s3_client(self) -> None:
        """S3 클라이언트 초기화"""
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.config["s3_region"],
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
            )
            logger.info("S3 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"S3 클라이언트 초기화 실패: {e}")
            self.s3_client = None
    
    async def save_screenshot(
        self,
        image_data: bytes,
        keyword: str,
        platform: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        스크린샷 이미지 저장
        
        Args:
            image_data: 이미지 바이트 데이터
            keyword: 키워드
            platform: 플랫폼
            metadata: 추가 메타데이터
            
        Returns:
            Dict[str, Any]: 저장 결과
        """
        try:
            # 이미지 메타데이터 추출
            image_metadata = await self._extract_image_metadata(image_data)
            
            # 파일 경로 생성
            file_path = self._generate_file_path(keyword, platform, image_metadata["format"])
            
            # 이미지 최적화
            optimized_image_data = await self._optimize_image(image_data)
            
            # 로컬 저장소에 저장
            local_path = await self._save_to_local_storage(optimized_image_data, file_path)
            
            # S3에 저장 (설정된 경우)
            s3_url = None
            if self.s3_client:
                s3_url = await self._save_to_s3(optimized_image_data, file_path)
            
            # 썸네일 생성
            thumbnail_path = None
            if self.config["enable_thumbnail"]:
                thumbnail_path = await self._create_thumbnail(optimized_image_data, file_path)
            
            # 메타데이터 저장
            metadata_record = await self._save_metadata(
                file_path=local_path,
                s3_url=s3_url,
                thumbnail_path=thumbnail_path,
                keyword=keyword,
                platform=platform,
                image_metadata=image_metadata,
                additional_metadata=metadata
            )
            
            return {
                "success": True,
                "file_path": local_path,
                "s3_url": s3_url,
                "thumbnail_path": thumbnail_path,
                "metadata_id": metadata_record["metadata_id"],
                "file_size": len(optimized_image_data),
                "optimized": True
            }
            
        except Exception as e:
            logger.error(f"스크린샷 저장 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _extract_image_metadata(self, image_data: bytes) -> Dict[str, Any]:
        """이미지 메타데이터 추출"""
        try:
            # PIL을 사용하여 이미지 정보 추출
            from io import BytesIO
            image = Image.open(BytesIO(image_data))
            
            return {
                "format": image.format,
                "size": image.size,
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "file_size": len(image_data),
                "hash": hashlib.md5(image_data).hexdigest(),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"이미지 메타데이터 추출 실패: {e}")
            return {
                "format": "Unknown",
                "size": (0, 0),
                "width": 0,
                "height": 0,
                "mode": "Unknown",
                "file_size": len(image_data),
                "hash": hashlib.md5(image_data).hexdigest(),
                "created_at": datetime.now().isoformat()
            }
    
    def _generate_file_path(self, keyword: str, platform: str, format: str) -> str:
        """파일 경로 생성"""
        # 안전한 파일명 생성
        safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_keyword = safe_keyword.replace(' ', '_')
        
        # 타임스탬프 추가
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 해시 추가 (중복 방지)
        hash_part = hashlib.md5(f"{keyword}_{platform}_{timestamp}".encode()).hexdigest()[:8]
        
        file_extension = format.lower() if format else "png"
        filename = f"{safe_keyword}_{timestamp}_{hash_part}.{file_extension}"
        
        return f"{platform}/{filename}"
    
    async def _optimize_image(self, image_data: bytes) -> bytes:
        """이미지 최적화"""
        if not self.config["enable_compression"]:
            return image_data
        
        try:
            from io import BytesIO
            
            # 이미지 로드
            image = Image.open(BytesIO(image_data))
            
            # 크기 조정
            if max(image.size) > self.config["max_image_size"]:
                image.thumbnail((self.config["max_image_size"], self.config["max_image_size"]), Image.Resampling.LANCZOS)
            
            # RGB 변환 (JPEG 저장을 위해)
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            
            # 최적화된 이미지 저장
            output = BytesIO()
            image.save(
                output,
                format="JPEG",
                quality=self.config["image_quality"],
                optimize=True
            )
            
            optimized_data = output.getvalue()
            
            # 압축 효과 로깅
            original_size = len(image_data)
            compressed_size = len(optimized_data)
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            logger.info(f"이미지 압축 완료: {original_size} -> {compressed_size} bytes ({compression_ratio:.1f}% 감소)")
            
            return optimized_data
            
        except Exception as e:
            logger.error(f"이미지 최적화 실패: {e}")
            return image_data
    
    async def _save_to_local_storage(self, image_data: bytes, file_path: str) -> str:
        """로컬 저장소에 저장"""
        try:
            full_path = self.local_storage_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(image_data)
            
            logger.info(f"로컬 저장소에 저장 완료: {full_path}")
            return str(full_path)
            
        except Exception as e:
            logger.error(f"로컬 저장소 저장 실패: {e}")
            raise
    
    async def _save_to_s3(self, image_data: bytes, file_path: str) -> Optional[str]:
        """S3에 저장"""
        if not self.s3_client:
            return None
        
        try:
            # S3 키 생성
            s3_key = f"screenshots/{file_path}"
            
            # 메타데이터 설정
            metadata = {
                'Content-Type': 'image/jpeg',
                'Cache-Control': 'max-age=86400',
                'Content-Disposition': 'inline'
            }
            
            # S3에 업로드
            self.s3_client.put_object(
                Bucket=self.config["s3_bucket"],
                Key=s3_key,
                Body=image_data,
                **metadata
            )
            
            # URL 생성
            s3_url = f"https://{self.config['s3_bucket']}.s3.{self.config['s3_region']}.amazonaws.com/{s3_key}"
            
            logger.info(f"S3 저장 완료: {s3_url}")
            return s3_url
            
        except ClientError as e:
            logger.error(f"S3 저장 실패: {e}")
            return None
    
    async def _create_thumbnail(self, image_data: bytes, file_path: str) -> Optional[str]:
        """썸네일 생성"""
        try:
            from io import BytesIO
            
            # 이미지 로드
            image = Image.open(BytesIO(image_data))
            
            # 썸네일 생성
            thumbnail = image.copy()
            thumbnail.thumbnail(self.config["thumbnail_size"], Image.Resampling.LANCZOS)
            
            # 썸네일 저장
            thumbnail_path = file_path.replace(".", "_thumb.")
            full_thumbnail_path = self.local_storage_path / thumbnail_path
            full_thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            
            # RGB 변환
            if thumbnail.mode in ("RGBA", "P"):
                thumbnail = thumbnail.convert("RGB")
            
            thumbnail.save(full_thumbnail_path, format="JPEG", quality=70)
            
            logger.info(f"썸네일 생성 완료: {full_thumbnail_path}")
            return str(full_thumbnail_path)
            
        except Exception as e:
            logger.error(f"썸네일 생성 실패: {e}")
            return None
    
    async def _save_metadata(
        self,
        file_path: str,
        s3_url: Optional[str],
        thumbnail_path: Optional[str],
        keyword: str,
        platform: str,
        image_metadata: Dict[str, Any],
        additional_metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """메타데이터 저장"""
        try:
            metadata_id = hashlib.md5(f"{file_path}_{datetime.now().isoformat()}".encode()).hexdigest()
            
            metadata_record = {
                "metadata_id": metadata_id,
                "file_path": file_path,
                "s3_url": s3_url or "",
                "thumbnail_path": thumbnail_path or "",
                "keyword": keyword,
                "platform": platform,
                "image_format": image_metadata.get("format", "Unknown"),
                "image_width": image_metadata.get("width", 0),
                "image_height": image_metadata.get("height", 0),
                "file_size": image_metadata.get("file_size", 0),
                "image_hash": image_metadata.get("hash", ""),
                "created_at": datetime.now(),
                "additional_metadata": json.dumps(additional_metadata or {}),
                "storage_type": "local_s3" if s3_url else "local",
                "optimization_applied": self.config["enable_compression"],
                "thumbnail_created": bool(thumbnail_path)
            }
            
            # 데이터베이스에 저장
            self.db_client.insert("image_metadata", [metadata_record])
            
            # Redis 캐시에 저장
            await self.redis_client.setex(
                f"image_metadata:{metadata_id}",
                self.config["cache_ttl"],
                json.dumps(metadata_record, default=str)
            )
            
            logger.info(f"메타데이터 저장 완료: {metadata_id}")
            return metadata_record
            
        except Exception as e:
            logger.error(f"메타데이터 저장 실패: {e}")
            raise
    
    async def get_image_metadata(self, metadata_id: str) -> Dict[str, Any]:
        """이미지 메타데이터 조회"""
        try:
            # Redis 캐시 확인
            cached_data = await self.redis_client.get(f"image_metadata:{metadata_id}")
            if cached_data:
                return json.loads(cached_data)
            
            # 데이터베이스 조회
            query = f"SELECT * FROM image_metadata WHERE metadata_id = '{metadata_id}'"
            result = self.db_client.query(query)
            
            if result.result_rows:
                metadata = {
                    "metadata_id": result.result_rows[0][0],
                    "file_path": result.result_rows[0][1],
                    "s3_url": result.result_rows[0][2],
                    "thumbnail_path": result.result_rows[0][3],
                    "keyword": result.result_rows[0][4],
                    "platform": result.result_rows[0][5],
                    "image_format": result.result_rows[0][6],
                    "image_width": result.result_rows[0][7],
                    "image_height": result.result_rows[0][8],
                    "file_size": result.result_rows[0][9],
                    "image_hash": result.result_rows[0][10],
                    "created_at": result.result_rows[0][11],
                    "additional_metadata": json.loads(result.result_rows[0][12] or "{}"),
                    "storage_type": result.result_rows[0][13],
                    "optimization_applied": result.result_rows[0][14],
                    "thumbnail_created": result.result_rows[0][15]
                }
                
                # 캐시에 저장
                await self.redis_client.setex(
                    f"image_metadata:{metadata_id}",
                    self.config["cache_ttl"],
                    json.dumps(metadata, default=str)
                )
                
                return metadata
            
            return {"error": "메타데이터를 찾을 수 없습니다"}
            
        except Exception as e:
            logger.error(f"메타데이터 조회 실패: {e}")
            return {"error": str(e)}
    
    async def cleanup_old_images(self, retention_days: Optional[int] = None) -> Dict[str, Any]:
        """오래된 이미지 정리"""
        try:
            retention_days = retention_days or self.config["retention_days"]
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # 정리 대상 이미지 조회
            query = f"""
            SELECT metadata_id, file_path, s3_url, thumbnail_path
            FROM image_metadata
            WHERE created_at < '{cutoff_date.isoformat()}'
            """
            
            result = self.db_client.query(query)
            old_images = result.result_rows
            
            cleaned_count = 0
            errors = []
            
            for image_record in old_images:
                metadata_id, file_path, s3_url, thumbnail_path = image_record
                
                try:
                    # 로컬 파일 삭제
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                    
                    # 썸네일 삭제
                    if thumbnail_path and os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                    
                    # S3 파일 삭제
                    if s3_url and self.s3_client:
                        s3_key = s3_url.split('/')[-1]
                        self.s3_client.delete_object(
                            Bucket=self.config["s3_bucket"],
                            Key=f"screenshots/{s3_key}"
                        )
                    
                    # 메타데이터 삭제
                    delete_query = f"DELETE FROM image_metadata WHERE metadata_id = '{metadata_id}'"
                    self.db_client.query(delete_query)
                    
                    # 캐시 삭제
                    await self.redis_client.delete(f"image_metadata:{metadata_id}")
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    errors.append(f"이미지 {metadata_id} 정리 실패: {e}")
            
            logger.info(f"이미지 정리 완료: {cleaned_count}개 삭제, {len(errors)}개 오류")
            
            return {
                "success": True,
                "cleaned_count": cleaned_count,
                "errors": errors,
                "retention_days": retention_days
            }
            
        except Exception as e:
            logger.error(f"이미지 정리 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """저장소 통계 조회"""
        try:
            # 전체 이미지 수
            total_query = "SELECT COUNT(*) FROM image_metadata"
            total_result = self.db_client.query(total_query)
            total_images = total_result.result_rows[0][0]
            
            # 플랫폼별 통계
            platform_query = """
            SELECT platform, COUNT(*), SUM(file_size), AVG(file_size)
            FROM image_metadata
            GROUP BY platform
            """
            platform_result = self.db_client.query(platform_query)
            platform_stats = {
                row[0]: {
                    "count": row[1],
                    "total_size": row[2],
                    "avg_size": row[3]
                }
                for row in platform_result.result_rows
            }
            
            # 최근 7일 통계
            recent_query = """
            SELECT DATE(created_at) as date, COUNT(*), SUM(file_size)
            FROM image_metadata
            WHERE created_at >= NOW() - INTERVAL 7 DAY
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            """
            recent_result = self.db_client.query(recent_query)
            recent_stats = {
                str(row[0]): {
                    "count": row[1],
                    "total_size": row[2]
                }
                for row in recent_result.result_rows
            }
            
            # 저장소 타입별 통계
            storage_query = """
            SELECT storage_type, COUNT(*), SUM(file_size)
            FROM image_metadata
            GROUP BY storage_type
            """
            storage_result = self.db_client.query(storage_query)
            storage_stats = {
                row[0]: {
                    "count": row[1],
                    "total_size": row[2]
                }
                for row in storage_result.result_rows
            }
            
            return {
                "total_images": total_images,
                "platform_statistics": platform_stats,
                "recent_statistics": recent_stats,
                "storage_statistics": storage_stats,
                "config": {
                    "retention_days": self.config["retention_days"],
                    "use_s3": self.config["use_s3"],
                    "enable_compression": self.config["enable_compression"],
                    "enable_thumbnail": self.config["enable_thumbnail"]
                }
            }
            
        except Exception as e:
            logger.error(f"저장소 통계 조회 실패: {e}")
            return {"error": str(e)}


# 이미지 저장소 테이블 스키마 (필요시 데이터베이스에 추가)
IMAGE_METADATA_SCHEMA = """
CREATE TABLE IF NOT EXISTS image_metadata (
    metadata_id String,
    file_path String,
    s3_url String DEFAULT '',
    thumbnail_path String DEFAULT '',
    keyword String,
    platform String,
    image_format String,
    image_width UInt32,
    image_height UInt32,
    file_size UInt64,
    image_hash String,
    created_at DateTime DEFAULT now(),
    additional_metadata String DEFAULT '{}',
    storage_type String DEFAULT 'local',
    optimization_applied UInt8 DEFAULT 0,
    thumbnail_created UInt8 DEFAULT 0
) ENGINE = MergeTree()
ORDER BY (platform, created_at)
SETTINGS index_granularity = 8192;
"""