import React, { useState, useEffect } from "react";
import {
  Modal,
  Form,
  Switch,
  Slider,
  Card,
  Typography,
  Space,
  Button,
  Divider,
  Tooltip,
} from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";
import { safeToFixed, safeToPercent, safeNumber } from "../utils/formatters";

const { Title, Text } = Typography;

const EvaluatorConfigModal = ({ visible, configs, onSave, onCancel }) => {
  const [form] = Form.useForm();
  const [localConfigs, setLocalConfigs] = useState({});

  useEffect(() => {
    if (visible && configs) {
      setLocalConfigs(configs);
      form.setFieldsValue(configs);
    }
  }, [visible, configs, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      await onSave(values);
      onCancel();
    } catch (error) {
      console.error("설정 저장 실패:", error);
    }
  };

  const evaluatorInfo = {
    rule_based: {
      name: "Rule 기반",
      description: "브랜드, 카테고리 등 메타데이터를 기반으로 자동 정답 판단",
      pros: "빠른 처리, 일관된 결과",
      cons: "제한적인 판단 기준",
    },
    keyword: {
      name: "Keyword 기반",
      description: "상품명/설명에 키워드 포함 여부로 정답 판단",
      pros: "직관적, 투명한 로직",
      cons: "동의어 처리 한계",
    },
    llm: {
      name: "LLM 기반",
      description: "GPT 등 대형 언어 모델로 검색 결과의 적절성 판단",
      pros: "높은 정확도, 맥락 이해",
      cons: "비용, 처리 시간",
    },
    embedding: {
      name: "Embedding 기반",
      description: "쿼리와 상품 간 텍스트/이미지 임베딩 유사도 측정",
      pros: "의미적 유사도, 다국어 지원",
      cons: "모델 의존성, 계산 복잡도",
    },
    individual_image_llm: {
      name: "Individual Image LLM",
      description: "각 상품 이미지를 개별적으로 LLM에게 평가받는 고정밀도 평가",
      pros: "매우 높은 정확도, 세밀한 분석",
      cons: "높은 비용, 긴 처리 시간",
      warning:
        "⚠️ 이 기능은 많은 API 호출을 발생시켜 비용이 많이 들 수 있습니다",
    },
  };

  const renderEvaluatorCard = (key, config) => {
    const info = evaluatorInfo[key];
    if (!info) return null;

    return (
      <Card key={key} className="mb-4" size="small">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Title level={5} className="mb-0">
              {info.name}
            </Title>
            <Tooltip title={info.description}>
              <InfoCircleOutlined className="text-gray-400" />
            </Tooltip>
          </div>
          <Form.Item
            name={[key, "enabled"]}
            valuePropName="checked"
            className="mb-0"
          >
            <Switch size="small" />
          </Form.Item>
        </div>

        <Text className="text-sm text-gray-600 block mb-3">
          {info.description}
        </Text>

        <div className="grid grid-cols-2 gap-4 mb-4 text-xs">
          <div>
            <Text className="text-green-600 font-medium">장점:</Text>
            <Text className="block text-gray-600">{info.pros}</Text>
          </div>
          <div>
            <Text className="text-orange-600 font-medium">단점:</Text>
            <Text className="block text-gray-600">{info.cons}</Text>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <Text className="text-sm font-medium">가중치</Text>
              <Text className="text-sm text-gray-500">
                {safeToPercent((localConfigs[key]?.weight || 0) * 100)}
              </Text>
            </div>
            <Form.Item name={[key, "weight"]} className="mb-0">
              <Slider
                min={0}
                max={1}
                step={0.1}
                onChange={(value) => {
                  handleWeightChange(key, value);
                }}
                marks={{
                  0: "0%",
                  0.5: "50%",
                  1: "100%",
                }}
              />
            </Form.Item>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <Text className="text-sm font-medium">최소 신뢰도 임계값</Text>
              <Text className="text-sm text-gray-500">
                {safeToPercent(
                  (localConfigs[key]?.confidence_threshold || 0) * 100
                )}
              </Text>
            </div>
            <Form.Item name={[key, "confidence_threshold"]} className="mb-0">
              <Slider
                min={0}
                max={1}
                step={0.1}
                onChange={(value) => {
                  setLocalConfigs((prev) => ({
                    ...prev,
                    [key]: { ...prev[key], confidence_threshold: value },
                  }));
                }}
                marks={{
                  0: "0%",
                  0.5: "50%",
                  1: "100%",
                }}
              />
            </Form.Item>
          </div>
        </div>
      </Card>
    );
  };

  const getTotalWeight = () => {
    const standardEvaluators = Object.entries(localConfigs).reduce(
      (total, [key, config]) => {
        if (key === "individual_image_llm") return total; // 별도 처리
        return total + (config.enabled ? config.weight || 0 : 0);
      },
      0
    );

    const individualImageLLMWeight = localConfigs.individual_image_llm?.enabled
      ? localConfigs.individual_image_llm?.weight || 0
      : 0;

    return standardEvaluators + individualImageLLMWeight;
  };

  const isWeightBalanced = () => {
    const total = getTotalWeight();
    return Math.abs(total - 1.0) < 0.01;
  };

  const handleIndividualImageLLMToggle = (enabled) => {
    const currentConfigs = { ...localConfigs };

    if (enabled) {
      // Individual Image LLM 활성화 시
      const individualWeight = 0.2; // Individual Image LLM 기본 가중치
      const otherEvaluators = ["rule_based", "keyword", "llm", "embedding"];

      // 현재 활성화된 다른 평가기들의 가중치 합계 계산
      const currentActiveWeight = otherEvaluators.reduce((sum, key) => {
        return (
          sum +
          (currentConfigs[key]?.enabled ? currentConfigs[key]?.weight || 0 : 0)
        );
      }, 0);

      // 나머지 가중치를 다른 평가기들에 비례 배분
      const remainingWeight = 1.0 - individualWeight;
      const scaleFactor =
        currentActiveWeight > 0 ? remainingWeight / currentActiveWeight : 0;

      // 각 평가기의 가중치 조정
      otherEvaluators.forEach((key) => {
        if (currentConfigs[key]?.enabled) {
          currentConfigs[key] = {
            ...currentConfigs[key],
            weight: (currentConfigs[key]?.weight || 0) * scaleFactor,
          };
        }
      });

      // Individual Image LLM 설정
      currentConfigs.individual_image_llm = {
        ...currentConfigs.individual_image_llm,
        enabled: true,
        weight: individualWeight,
      };
    } else {
      // Individual Image LLM 비활성화 시
      const individualWeight = currentConfigs.individual_image_llm?.weight || 0;
      const otherEvaluators = ["rule_based", "keyword", "llm", "embedding"];

      // 현재 활성화된 다른 평가기들의 가중치 합계 계산
      const currentActiveWeight = otherEvaluators.reduce((sum, key) => {
        return (
          sum +
          (currentConfigs[key]?.enabled ? currentConfigs[key]?.weight || 0 : 0)
        );
      }, 0);

      // Individual Image LLM의 가중치를 다른 활성화된 평가기들에 비례 배분
      if (currentActiveWeight > 0) {
        const redistributeWeight = individualWeight;
        const scaleFactor =
          (currentActiveWeight + redistributeWeight) / currentActiveWeight;

        otherEvaluators.forEach((key) => {
          if (currentConfigs[key]?.enabled) {
            currentConfigs[key] = {
              ...currentConfigs[key],
              weight: (currentConfigs[key]?.weight || 0) * scaleFactor,
            };
          }
        });
      }

      // Individual Image LLM 비활성화
      currentConfigs.individual_image_llm = {
        ...currentConfigs.individual_image_llm,
        enabled: false,
      };
    }

    setLocalConfigs(currentConfigs);
    form.setFieldsValue(currentConfigs);
  };

  const handleWeightChange = (evaluatorKey, newWeight) => {
    const currentConfigs = { ...localConfigs };
    const oldWeight = currentConfigs[evaluatorKey]?.weight || 0;
    const weightDiff = newWeight - oldWeight;

    // 현재 평가기 가중치 업데이트
    currentConfigs[evaluatorKey] = {
      ...currentConfigs[evaluatorKey],
      weight: newWeight,
    };

    // 다른 활성화된 평가기들에서 비례적으로 가중치 차감/추가
    const otherEvaluators = Object.keys(currentConfigs).filter(
      (key) => key !== evaluatorKey && currentConfigs[key]?.enabled
    );

    if (otherEvaluators.length > 0 && Math.abs(weightDiff) > 0.001) {
      const totalOtherWeight = otherEvaluators.reduce(
        (sum, key) => sum + (currentConfigs[key]?.weight || 0),
        0
      );

      if (totalOtherWeight > 0) {
        const adjustmentFactor =
          Math.max(0, totalOtherWeight - weightDiff) / totalOtherWeight;

        otherEvaluators.forEach((key) => {
          currentConfigs[key] = {
            ...currentConfigs[key],
            weight: Math.max(
              0,
              (currentConfigs[key]?.weight || 0) * adjustmentFactor
            ),
          };
        });
      }
    }

    setLocalConfigs(currentConfigs);
  };

  return (
    <Modal
      title="다중 평가 시스템 설정"
      open={visible}
      onCancel={onCancel}
      width={800}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          취소
        </Button>,
        <Button
          key="save"
          type="primary"
          onClick={handleSave}
          disabled={!isWeightBalanced()}
        >
          저장
        </Button>,
      ]}
    >
      <div className="max-h-[600px] overflow-y-auto">
        <div className="mb-4 p-3 bg-blue-50 rounded border border-blue-200">
          <Title level={5} className="text-blue-800 mb-2">
            다중 평가 시스템이란?
          </Title>
          <Text className="text-blue-700 text-sm">
            여러 평가 방식을 조합하여 더 정확하고 신뢰할 수 있는 검색 품질
            측정을 제공합니다. 각 평가기의 가중치와 신뢰도 임계값을 조정하여
            최적의 평가 결과를 얻을 수 있습니다.
          </Text>
        </div>

        <div className="mb-4 p-3 bg-gray-50 rounded">
          <div className="flex items-center justify-between">
            <Text className="font-medium">총 가중치:</Text>
            <Text
              className={`font-bold ${
                isWeightBalanced() ? "text-green-600" : "text-red-600"
              }`}
            >
              {safeToPercent(getTotalWeight() * 100)}
            </Text>
          </div>
          {!isWeightBalanced() && (
            <Text className="text-red-600 text-sm mt-1">
              ⚠️ 활성화된 평가기들의 총 가중치가 100%가 되어야 합니다.
            </Text>
          )}
          {isWeightBalanced() && (
            <Text className="text-green-600 text-sm mt-1">
              ✅ 가중치 균형이 맞춰졌습니다.
            </Text>
          )}
        </div>

        <Form form={form} layout="vertical">
          {Object.entries(configs)
            .filter(([key]) => key !== "individual_image_llm") // individual_image_llm 제외
            .map(([key, config]) => renderEvaluatorCard(key, config))}

          {/* Individual Image LLM 평가기 - 별도 카드 */}
          {configs.individual_image_llm && (
            <Card className="mb-4">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <Title level={4} className="mb-1">
                    {evaluatorInfo.individual_image_llm.name}
                    <Tooltip title={evaluatorInfo.individual_image_llm.warning}>
                      <InfoCircleOutlined className="ml-2 text-orange-500" />
                    </Tooltip>
                  </Title>
                  <Text className="text-gray-600">
                    {evaluatorInfo.individual_image_llm.description}
                  </Text>
                  {evaluatorInfo.individual_image_llm.warning && (
                    <div className="mt-2 p-2 bg-orange-50 border border-orange-200 rounded">
                      <Text className="text-orange-700 text-sm">
                        {evaluatorInfo.individual_image_llm.warning}
                      </Text>
                    </div>
                  )}
                </div>
                <Form.Item
                  name={["individual_image_llm", "enabled"]}
                  valuePropName="checked"
                  className="mb-0"
                >
                  <Switch onChange={handleIndividualImageLLMToggle} />
                </Form.Item>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <Text strong className="text-green-600">
                    장점:
                  </Text>
                  <br />
                  <Text>{evaluatorInfo.individual_image_llm.pros}</Text>
                </div>
                <div>
                  <Text strong className="text-red-600">
                    단점:
                  </Text>
                  <br />
                  <Text>{evaluatorInfo.individual_image_llm.cons}</Text>
                </div>
              </div>

              <div className="space-y-3 mt-4">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <Text className="text-sm font-medium">가중치</Text>
                    <Text className="text-sm text-gray-500">
                      {safeToPercent(
                        (localConfigs.individual_image_llm?.weight || 0.3) * 100
                      )}
                    </Text>
                  </div>
                  <Form.Item
                    name={["individual_image_llm", "weight"]}
                    className="mb-0"
                  >
                    <Slider
                      min={0}
                      max={1}
                      step={0.1}
                      disabled={!localConfigs.individual_image_llm?.enabled}
                      onChange={(value) => {
                        handleWeightChange("individual_image_llm", value);
                      }}
                      marks={{
                        0: "0%",
                        0.5: "50%",
                        1: "100%",
                      }}
                    />
                  </Form.Item>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <Text className="text-sm font-medium">
                      최소 신뢰도 임계값
                    </Text>
                    <Text className="text-sm text-gray-500">
                      {safeToPercent(
                        (localConfigs.individual_image_llm
                          ?.confidence_threshold || 0.5) * 100
                      )}
                    </Text>
                  </div>
                  <Form.Item
                    name={["individual_image_llm", "confidence_threshold"]}
                    className="mb-0"
                  >
                    <Slider
                      min={0}
                      max={1}
                      step={0.1}
                      disabled={!localConfigs.individual_image_llm?.enabled}
                      onChange={(value) => {
                        setLocalConfigs((prev) => ({
                          ...prev,
                          individual_image_llm: {
                            ...prev.individual_image_llm,
                            confidence_threshold: value,
                          },
                        }));
                      }}
                      marks={{
                        0: "0%",
                        0.5: "50%",
                        1: "100%",
                      }}
                    />
                  </Form.Item>
                </div>

                {/* 평가할 최대 상품 수 */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <Text className="text-sm font-medium">
                      평가할 최대 상품 수
                    </Text>
                    <Text className="text-sm text-gray-500">
                      {localConfigs.individual_image_llm?.max_products || 50}개
                    </Text>
                  </div>
                  <Form.Item
                    name={["individual_image_llm", "max_products"]}
                    className="mb-0"
                  >
                    <Slider
                      min={1}
                      max={50}
                      step={1}
                      disabled={!localConfigs.individual_image_llm?.enabled}
                      onChange={(value) => {
                        setLocalConfigs((prev) => ({
                          ...prev,
                          individual_image_llm: {
                            ...prev.individual_image_llm,
                            max_products: value,
                          },
                        }));
                      }}
                      marks={{
                        1: "1",
                        10: "10",
                        25: "25",
                        50: "50",
                      }}
                    />
                  </Form.Item>
                </div>
              </div>
            </Card>
          )}
        </Form>

        <Divider />

        <div className="text-xs text-gray-500">
          <Title level={5} className="text-gray-700">
            설정 가이드:
          </Title>
          <ul className="space-y-1">
            <li>
              • <strong>가중치:</strong> 최종 점수 계산 시 각 평가기의 영향력을
              결정합니다.
            </li>
            <li>
              • <strong>신뢰도 임계값:</strong> 이 값보다 낮은 신뢰도의 결과는
              최종 계산에서 제외됩니다.
            </li>
            <li>
              • <strong>권장 설정:</strong> LLM 40%, Rule 30%, Keyword 20%,
              Embedding 10%
            </li>
          </ul>
        </div>
      </div>
    </Modal>
  );
};

export default EvaluatorConfigModal;
