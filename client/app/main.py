import streamlit as st
import asyncio
import httpx
from graph.gen import generate_graph_image

LOAD_FILE_URL = "http://graph-builder:8055/graph-builder/api/upload"
QA_RAG_URL = "http://qa-service:8000/api/question-answering/rag"
QA_LLM_URL = "http://qa-service:8000/api/question-answering/llm"

# Async function to upload file
async def upload_file(file):
    async with httpx.AsyncClient(timeout=300.0) as client:
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = await client.post(url=LOAD_FILE_URL,files=files)
        return response.json()

# Async function to query services
async def query_services(user_question):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response_task = client.post(
            url=QA_RAG_URL,
            json={"question": user_question}
        )
        control_task = client.post(
            url=QA_LLM_URL,
            json={"question": user_question}
        )
        rag_base_response, pure_llm_response = await asyncio.gather(
            response_task, control_task
        )
        return rag_base_response.json(), pure_llm_response.json()


if __name__ == "__main__":
    # --- Streamlit UI ---
    st.title("🔒 Security Analyst AI Assistant")
    st.write("I am here to help you!")

    with st.sidebar:
        st.header("📁 Upload File")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["txt"],
            help="Upload a document to analyze",
            disabled=st.session_state.get("pending_upload", None) is not None
        )

        if "upload_message" in st.session_state:
            msg_type, msg_text, msg_data = st.session_state["upload_message"]
            if msg_type == "success":
                st.success(msg_text)
                if msg_data:
                    st.json(msg_data)
            elif msg_type == "error":
                st.error(msg_text)
                if msg_data:
                    st.json(msg_data)
            del st.session_state["upload_message"]

        if uploaded_file is not None:
            if st.button("Upload File",disabled=st.session_state.get("pending_upload", None) is not None):
                st.session_state["pending_upload"] = uploaded_file
                st.rerun()

        if st.session_state.get("pending_upload", None) is not None:
            file_to_upload = st.session_state["pending_upload"]
            with st.spinner(f"Uploading {file_to_upload.name}..."):
                try:
                    result = asyncio.run(upload_file(file_to_upload))
                    del st.session_state["pending_upload"]

                    if result.get("status") == "success":
                        st.session_state["upload_message"] = (
                            "success",
                            f"File uploaded: {file_to_upload.name}",
                            result
                        )
                    else:
                        st.session_state["upload_message"] = (
                            "error",
                            "File upload failed",
                            result
                        )

                except Exception as e:
                    del st.session_state["pending_upload"]
                    st.session_state["upload_message"] = ("error",f"❌ Error: {str(e)}", None)
            st.rerun()

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle new user input
    if user_input := st.chat_input("Enter your question..."):
        st.session_state["messages"].append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        rag_response, control_response = asyncio.run(query_services(user_input))

        cypher_query = rag_response.get("query")
        results = rag_response.get("answer")
        context_triples = rag_response.get("context")

        path_img = generate_graph_image(context_triples)

        llm_answer = control_response.get("answer")

        # Display AI assistant's main response
        with st.chat_message("assistant"):
            st.markdown(results)

        # Save assistant response to chat history
        st.session_state["messages"].append({"role": "assistant", "content": results})

        # Expandable sections for additional details
        with st.expander("🔍 Show LLM Answer"):
            st.markdown(llm_answer)

        with st.expander("📚 Show Context"):
            st.image(path_img, caption="Graph Visualization", width='stretch')

        with st.expander("📊 Show Generated Cypher Query"):
            st.code(cypher_query, language="cypher")