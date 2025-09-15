#!/usr/bin/env python3
"""
Terminal Chat Interface for Alleato RAG Agent

A simple command-line interface to test the chat functionality.
"""

import requests
import json
import sys
from typing import List, Dict

class TerminalChat:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.session_id = None
        self.conversation_history: List[Dict[str, str]] = []
    
    def print_banner(self):
        """Print welcome banner."""
        print("\n" + "="*60)
        print("🤖 ALLEATO RAG AGENT - TERMINAL CHAT")
        print("="*60)
        print("Ask me about meetings, projects, or any business data!")
        print("\nCommands:")
        print("  /help    - Show this help")
        print("  /clear   - Clear conversation history")
        print("  /history - Show conversation history")
        print("  /quit    - Exit chat")
        print("  /status  - Check API status")
        print("\nExample questions:")
        print("  • What were the last meetings?")
        print("  • Tell me about the Uniqlo project")
        print("  • Show me recent project updates")
        print("="*60 + "\n")
    
    def check_api_status(self):
        """Check if the API is running."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API Status: {data.get('status', 'unknown')}")
                print(f"   Database: {'✅' if data.get('checks', {}).get('database_connection') else '❌'}")
                print(f"   LLM: {'✅' if data.get('checks', {}).get('llm_configured') else '❌'}")
                return True
            else:
                print(f"❌ API returned status: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to API at {self.api_url}")
            print("   Make sure the server is running with: python -m uvicorn main:app --reload --port 8000")
            return False
        except Exception as e:
            print(f"❌ Error checking API: {e}")
            return False
    
    def send_message(self, message: str) -> bool:
        """Send message to the RAG agent."""
        try:
            payload = {
                "message": message,
                "conversation_history": self.conversation_history[-10:],  # Last 10 messages
                "session_id": self.session_id
            }
            
            print("🤔 Thinking...")
            response = requests.post(
                f"{self.api_url}/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Update session ID
                if not self.session_id:
                    self.session_id = data.get("session_id")
                
                # Add to conversation history
                self.conversation_history.append({"role": "user", "content": message})
                self.conversation_history.append({"role": "assistant", "content": data["response"]})
                
                # Print response
                print(f"\n🤖 Assistant:")
                print("-" * 50)
                print(data["response"])
                
                # Show tool usage if any
                if data.get("tool_calls"):
                    print(f"\n🔧 Tools used: {', '.join([tc['tool'] for tc in data['tool_calls']])}")
                
                print("-" * 50)
                return True
            else:
                print(f"❌ Error: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Details: {error_data}")
                except:
                    print(f"   Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out. The query might be complex - try again.")
            return False
        except requests.exceptions.ConnectionError:
            print("❌ Connection failed. Is the server running?")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def show_history(self):
        """Show conversation history."""
        if not self.conversation_history:
            print("📝 No conversation history yet.")
            return
        
        print("\n📜 Conversation History:")
        print("="*50)
        for i, msg in enumerate(self.conversation_history, 1):
            role = "👤 You" if msg["role"] == "user" else "🤖 Assistant"
            print(f"{i}. {role}: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}")
        print("="*50)
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.session_id = None
        print("🧹 Conversation history cleared.")
    
    def run(self):
        """Run the terminal chat interface."""
        self.print_banner()
        
        # Check API status first
        if not self.check_api_status():
            print("\n❌ Cannot start chat - API is not available.")
            return
        
        print("\n💬 Chat started! Type your message or /help for commands.\n")
        
        while True:
            try:
                # Get user input
                user_input = input("👤 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    command = user_input.lower()
                    
                    if command == '/quit' or command == '/exit':
                        print("\n👋 Goodbye!")
                        break
                    elif command == '/help':
                        self.print_banner()
                    elif command == '/clear':
                        self.clear_history()
                    elif command == '/history':
                        self.show_history()
                    elif command == '/status':
                        self.check_api_status()
                    else:
                        print(f"❓ Unknown command: {user_input}")
                        print("   Type /help for available commands.")
                    
                    print()  # Add spacing
                    continue
                
                # Send message to agent
                self.send_message(user_input)
                print()  # Add spacing for next message
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
            except EOFError:
                print("\n\n👋 Chat ended. Goodbye!")
                break

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Terminal chat interface for Alleato RAG Agent")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API URL (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    chat = TerminalChat(args.api_url)
    chat.run()

if __name__ == "__main__":
    main()