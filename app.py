"""The Streamlit application for the LLM Knowledge Hub."""
import streamlit as st
import ollama
import os

import context
import database
import injest


PAGE_TITLE = "LLM Knowledge Hub"
CONTEXT_NAME_DEFAULT = '(empty)'


def _parse(stream):
    """Parse the message content from the stream response."""
    for chunk in stream:
        yield chunk['message']['content']


def _get_context_options():
    """The context options include a default empty option and database items."""
    return [CONTEXT_NAME_DEFAULT] + database.list_collections()


def _load_data_from(folder_or_file: str):
    if os.path.exists(folder_or_file):
        try:
            with st.spinner(f"Injesting the data from {folder_or_file}..."):
                injest.add_folder_or_file(folder_or_file)
            st.success("Data successfully loaded!")
            st.rerun()

        except Exception as e:
            st.error(f"Failed to load data: {e}")
    else:
        st.error(f"Invalid Path! {folder_or_file}")

def _selectbox_model_on_change(key):
    model = st.session_state[key]
    if model.endswith(":32b"):
        st.session_state.context_size = 2048
    else:
        st.session_state.context_size = 4096


def _init_session_state(**kwargs):
    for key, value in kwargs.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_session_state(
    messages = [],
    context_size = 4096,
    )

st.set_page_config(initial_sidebar_state="collapsed")

st.title(PAGE_TITLE)

# Sidebar Configuration
with st.sidebar:
    st.markdown("# Config")
    model = st.selectbox(
        label = "Select the LLM model", 
        options = ["qwen2.5", "qwen2.5:14b", "qwen2.5:32b",
                   "qwen2.5-coder:32b"],
        index=1,
        key = "selectbox_model",
        on_change = _selectbox_model_on_change,
        args = ("selectbox_model",))
    context_name = st.selectbox(
        label = "Select the context",
        options = _get_context_options())
    with st.expander(label = "Advanced settings", expanded=False):
        context_size = st.select_slider(
            label = "Context size",
            options = [2048, 4096, 8192, 16384],
            value = st.session_state.context_size)
        num_retrieve = st.select_slider(
            label = "Number retrieve",
            options = [5, 10, 20, 30, 40, 50, 100],
            value = 20)
        score_threshold = st.select_slider(
            label = "Score threshold",
            options = [round(i * 0.1, 1) for i in range(11)],
            value=0.3)

    st.markdown("# Injest")      
    folder_or_file = st.text_input(
        label = "select a folder or file, click \"confirm\" to load.",
        value="/Volumes/business/Information")
    if st.button("Confirm"):
        _load_data_from(folder_or_file)

    st.markdown("# Chat")      
    if st.button("Reset chat"):
        st.session_state.messages = []


# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# User input for chat
if prompt:= st.chat_input("Type here to ask a question"):
    # Display user message in the chat interface
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Append the prompt for session state persistence
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Apply the template to include context information if the deault name 
    # (empty) is not selected. Otherwise, skip the context.
    if context_name != CONTEXT_NAME_DEFAULT:
        with st.spinner('Loading the context...'):
            context_information, metamsg = context.get_context(
                context_name, prompt, num_retrieve, score_threshold)
            print(metamsg) # display the meta message for the chat
            prompt = (
                f"Here is the related context\n\n {context_information}.\n\n"
                f"Answer the following question: {prompt}"
            )
    
    with st.spinner('Generating response...'):
        stream = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            options={"num_ctx": context_size},
        )
        response = st.write_stream(_parse(stream))

        # Append the response for session state persistence
        st.session_state.messages.append(
            {"role": "assistant", "content": response})
