"""
V2.02 智能增强模块
- 意图识别
- 实体抽取
- 质量评分
- 样本扩充
- 动态提示词
"""

from .intent_classifier import IntentClassifier
from .entity_extractor import EntityExtractor
from .quality_scorer import QualityScorer
from .sample_expander import SampleExpander
from .prompt_builder import PromptBuilder
from .intelligence_manager import IntelligenceManager
from .template_generator import TemplateGenerator, GeneratedReply
from .multi_sample_fusion import MultiSampleFusion, FusionResult, SampleInfo
from .entity_substitution import EntitySubstitutionGenerator, GeneratedResult
from .context_weighter import ContextWeighter, WeightAdjustment, ContextWindow
from .rule_inference_chain import RuleInferenceChain, InferenceResult

try:
    from .intelligence_manager_v204 import IntelligenceManagerV204, IntelligenceResultV204
    HAS_V204 = True
except ImportError:
    HAS_V204 = False

__all__ = [
    'IntentClassifier',
    'EntityExtractor',
    'QualityScorer',
    'SampleExpander',
    'PromptBuilder',
    'IntelligenceManager',
    'TemplateGenerator',
    'GeneratedReply',
    'MultiSampleFusion',
    'FusionResult',
    'SampleInfo',
    'EntitySubstitutionGenerator',
    'GeneratedResult',
    'ContextWeighter',
    'WeightAdjustment',
    'ContextWindow',
    'RuleInferenceChain',
    'InferenceResult',
]

if HAS_V204:
    __all__.extend(['IntelligenceManagerV204', 'IntelligenceResultV204'])
