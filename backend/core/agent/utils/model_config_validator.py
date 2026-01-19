"""模型配置验证工具"""
import os
import asyncio
import logging
from typing import Dict, List, Tuple
from backend.services.llm.model_config import get_model_config_manager
from backend.services.llm.llm_service import LLMService

logger = logging.getLogger(__name__)


class ModelConfigValidator:
    """模型配置验证器"""
    
    def __init__(self):
        self.config_manager = get_model_config_manager()
    
    def validate_all_configs(self) -> Dict[str, Dict[str, any]]:
        """
        验证所有模型配置
        
        Returns:
            验证结果字典
        """
        results = {}
        
        for model_type in ["chat", "code", "reasoning"]:
            try:
                config = self.config_manager.get_model_config_by_type(model_type)
                model_name = config.model_name
                
                # 检查 API Key
                api_key = os.environ.get(config.api_key_env)
                has_api_key = api_key is not None and len(api_key.strip()) >= 10
                
                results[model_type] = {
                    "model_name": model_name,
                    "provider": config.provider,
                    "api_key_env": config.api_key_env,
                    "has_api_key": has_api_key,
                    "base_url": self.config_manager.get_base_url(model_name),
                    "valid": has_api_key
                }
            except Exception as e:
                logger.error(f"验证 {model_type} 模型配置失败: {e}")
                results[model_type] = {
                    "valid": False,
                    "error": str(e)
                }
        
        return results
    
    async def test_api_keys(self) -> Dict[str, Dict[str, any]]:
        """
        测试所有配置的模型 API Key 是否可用
        
        Returns:
            测试结果字典
        """
        results = {}
        
        for model_type in ["chat", "code", "reasoning"]:
            try:
                config = self.config_manager.get_model_config_by_type(model_type)
                model_name = config.model_name
                
                logger.info(f"测试 {model_type} 模型 ({model_name})...")
                
                # 创建 LLMService 实例
                llm_service = LLMService(model=model_name)
                
                # 简单测试调用
                test_prompt = "测试"
                response = await llm_service.chat(user_prompt=test_prompt)
                
                results[model_type] = {
                    "model_name": model_name,
                    "provider": config.provider,
                    "api_key_available": True,
                    "test_successful": True,
                    "test_response_length": len(response) if isinstance(response, str) else 0
                }
                
                logger.info(f"✅ {model_type} 模型 ({model_name}) 测试成功")
                
            except Exception as e:
                logger.error(f"❌ {model_type} 模型测试失败: {e}")
                results[model_type] = {
                    "model_name": model_name if 'model_name' in locals() else "unknown",
                    "api_key_available": False,
                    "test_successful": False,
                    "error": str(e)
                }
        
        return results
    
    def print_validation_report(self, validation_results: Dict[str, Dict[str, any]]):
        """打印验证报告"""
        print("\n" + "="*60)
        print("模型配置验证报告")
        print("="*60)
        
        for model_type, result in validation_results.items():
            print(f"\n{model_type.upper()} 模型:")
            print(f"  模型名称: {result.get('model_name', 'N/A')}")
            print(f"  提供商: {result.get('provider', 'N/A')}")
            print(f"  API Key 环境变量: {result.get('api_key_env', 'N/A')}")
            print(f"  API Key 已配置: {'✅' if result.get('has_api_key') else '❌'}")
            
            if result.get('valid'):
                print(f"  状态: ✅ 配置有效")
            else:
                print(f"  状态: ❌ 配置无效")
                if 'error' in result:
                    print(f"  错误: {result['error']}")
        
        print("\n" + "="*60)
    
    def print_test_report(self, test_results: Dict[str, Dict[str, any]]):
        """打印测试报告"""
        print("\n" + "="*60)
        print("API Key 可用性测试报告")
        print("="*60)
        
        for model_type, result in test_results.items():
            print(f"\n{model_type.upper()} 模型:")
            print(f"  模型名称: {result.get('model_name', 'N/A')}")
            print(f"  提供商: {result.get('provider', 'N/A')}")
            print(f"  API Key 可用: {'✅' if result.get('api_key_available') else '❌'}")
            print(f"  测试成功: {'✅' if result.get('test_successful') else '❌'}")
            
            if result.get('test_successful'):
                print(f"  测试响应长度: {result.get('test_response_length', 0)} 字符")
            else:
                if 'error' in result:
                    print(f"  错误: {result['error']}")
        
        print("\n" + "="*60)
        
        # 总结
        all_valid = all(r.get('test_successful', False) for r in test_results.values())
        if all_valid:
            print("\n✅ 所有模型 API Key 测试通过！")
        else:
            print("\n❌ 部分模型 API Key 测试失败，请检查配置")


async def main():
    """主函数：执行验证和测试"""
    validator = ModelConfigValidator()
    
    # 1. 验证配置
    print("正在验证模型配置...")
    validation_results = validator.validate_all_configs()
    validator.print_validation_report(validation_results)
    
    # 2. 测试 API Key
    print("\n正在测试 API Key 可用性...")
    test_results = await validator.test_api_keys()
    validator.print_test_report(test_results)
    
    return validation_results, test_results


if __name__ == "__main__":
    asyncio.run(main())

