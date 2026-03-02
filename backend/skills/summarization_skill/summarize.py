import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

def summarize_conversation(messages: list) -> str:
    """
    Summarize conversation history using LiteLLM (GitHub Copilot/GPT-4o).
    
    Args:
        messages (list): List of dicts, e.g. [{"role": "user", "content": "..."}]
        
    Returns:
        str: The summary text.
    """
    
    # 1. Configuration
    # 尝试从环境变量获取，如果没有则使用占位符 (在实际使用中应确保环境变量存在)
    api_key = os.environ.get("LITELLM_API_KEY", "sk-placeholder") 
    base_url = "http://127.0.0.1:4000"
    model_name = "github_Copilot/gpt-4o"
    
    try:
        # 2. Initialize LLM
        llm = ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0.3
        )
        
        # 3. Convert messages to LangChain format
        langchain_msgs = []
        
        # System instruction
        system_prompt = (
            "你是一个专业的对话摘要助手。"
            "请阅读以下对话历史，并生成一个简洁的摘要。"
            "摘要应包含：主要讨论的话题、用户的核心需求、达成的结论。"
            "请用中文回答。"
        )
        langchain_msgs.append(SystemMessage(content=system_prompt))
        
        # Conversation history
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                langchain_msgs.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_msgs.append(AIMessage(content=content))
            # System messages in history are usually skipped or handled separately
            
        # Trigger instruction
        langchain_msgs.append(HumanMessage(content="请帮我总结以上对话的内容。"))
        
        # 4. Invoke
        response = llm.invoke(langchain_msgs)
        return response.content
        
    except Exception as e:
        return f"Error generating summary: {str(e)}"

if __name__ == "__main__":
    # Test case
    test_msgs = [
        {"role": "user", "content": "你好，我想了解Python"},
        {"role": "assistant", "content": "Python是一种广泛使用的高级编程语言..."},
    ]
    print(summarize_conversation(test_msgs))
