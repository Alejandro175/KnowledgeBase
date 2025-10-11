import streamlit as st
import requests

# --- Streamlit UI ---

st.title("🔒 Security Analyst AI Assistant")
st.write("I am here to help you!")

# Initialize chat message history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Render chat history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle new user input
if user_input := st.chat_input("Enter your question..."):
    st.session_state["messages"].append({"role": "user", "content": user_input})
    
    with st.chat_message("user"):
        st.markdown(user_input)

    # Query translation service (NL → Cypher)
    response = requests.post("http://qa-service:8000/api/answer/generate", json={"question": user_input})
    cypher_query = response.json().get("query")
    results = response.json().get("answer")
    context = response.json().get("context")

    control_reponse = requests.post("http://qa-service:8000/api/answer/direct", json={"question": user_input})
    llm_answer = control_reponse.json().get("answer")

    # Display AI assistant's main response
    with st.chat_message("assistant"):
        st.markdown(results)
    
    # Save assistant response to chat history
    st.session_state["messages"].append({"role": "assistant", "content": results})

    # Expandable sections for additional details
    with st.expander("🔍 Show LLM Answer"):
        st.markdown(llm_answer)

    with st.expander("📚 Show Context"):
        st.markdown(context)

    with st.expander("📊 Show Generated Cypher Query"):
        st.code(cypher_query, language="cypher")