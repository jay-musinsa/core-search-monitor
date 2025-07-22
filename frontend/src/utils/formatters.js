/**
 * 숫자 포맷팅 유틸리티 함수들
 */

/**
 * 안전한 숫자 포맷팅 (소수점)
 * @param {number|string|undefined|null} value - 포맷할 값
 * @param {number} decimals - 소수점 자릿수 (기본값: 3)
 * @returns {string} 포맷된 문자열
 */
export const safeToFixed = (value, decimals = 3) => {
  if (value === null || value === undefined || isNaN(value)) {
    return "0." + "0".repeat(decimals);
  }

  const num = typeof value === "string" ? parseFloat(value) : Number(value);
  if (isNaN(num)) {
    return "0." + "0".repeat(decimals);
  }

  return num.toFixed(decimals);
};

/**
 * 안전한 퍼센트 포맷팅
 * @param {number|string|undefined|null} value - 포맷할 값 (0-1 범위)
 * @param {number} decimals - 소수점 자릿수 (기본값: 1)
 * @returns {string} 퍼센트 문자열 (예: "85.2%")
 */
export const safeToPercent = (value, decimals = 1) => {
  if (value === null || value === undefined || isNaN(value)) {
    return "0%";
  }

  const num = typeof value === "string" ? parseFloat(value) : Number(value);
  if (isNaN(num)) {
    return "0%";
  }

  return (num * 100).toFixed(decimals) + "%";
};

/**
 * 안전한 정수 포맷팅
 * @param {number|string|undefined|null} value - 포맷할 값
 * @returns {string} 정수 문자열
 */
export const safeToInt = (value) => {
  if (value === null || value === undefined || isNaN(value)) {
    return "0";
  }

  const num = typeof value === "string" ? parseFloat(value) : Number(value);
  if (isNaN(num)) {
    return "0";
  }

  return Math.round(num).toString();
};

/**
 * 안전한 숫자 값 반환
 * @param {number|string|undefined|null} value - 확인할 값
 * @param {number} defaultValue - 기본값 (기본값: 0)
 * @returns {number} 안전한 숫자 값
 */
export const safeNumber = (value, defaultValue = 0) => {
  if (value === null || value === undefined || isNaN(value)) {
    return defaultValue;
  }

  const num = typeof value === "string" ? parseFloat(value) : Number(value);
  return isNaN(num) ? defaultValue : num;
};
