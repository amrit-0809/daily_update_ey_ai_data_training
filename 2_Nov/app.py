
import streamlit as st
import pandas as pd
import plotly.express as px

from benchmark import (
    run_benchmark,
    MODELS,
    CSV_PATH
)


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(

    page_title="RAG Model Benchmark",

    page_icon="⚡",

    layout="wide"

)


# ==========================================
# CUSTOM CSS
# ==========================================

st.markdown("""
<style>

.stApp {
    background-color: #0e1117;
}

[data-testid="stMetric"] {
    background-color: #1c2333;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #303849;
}

[data-testid="stSidebar"] {
    background-color: #151b28;
}

h1, h2, h3 {
    color: #f1f5f9;
}

.stButton button {
    background-color: #2563eb;
    color: white;
    border-radius: 8px;
    height: 45px;
    width: 100%;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# SESSION STATE
# ==========================================

if "benchmark_data" not in st.session_state:
    st.session_state.benchmark_data = None


# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.title("⚡ RAG Benchmark")

    st.caption("OpenRouter Model Performance")

    st.divider()

    st.subheader("Configuration")

    test_runs = st.selectbox(
        "Runs per model",
        [1, 3, 5, 10],
        index=1
    )

    st.subheader("Models")

    for model in MODELS:
        st.checkbox(
            model,
            value=True,
            disabled=True
        )

    st.divider()

    st.caption("Retrieval configuration")

    st.info(
        "Embedding model: Common embedding model\n\n"
        "Top K: 3\n\n"
        "Retrieval: Once per question"
    )


# ==========================================
# HEADER
# ==========================================

st.title("🚀 RAG Model Speed Benchmark")

st.markdown(
    "Compare OpenRouter free models using identical "
    "retrieved document context."
)

st.divider()


# ==========================================
# QUESTION INPUT
# ==========================================

st.subheader("Enter your question")

question = st.text_area(

    "Question",

    placeholder="What is the company's leave policy?",

    height=100,

    label_visibility="collapsed"

)


# ==========================================
# RUN BENCHMARK
# ==========================================

if st.button("🚀 Start Benchmark"):

    if not question.strip():

        st.warning("Please enter a question.")

    else:

        try:

            with st.spinner(
                "Retrieving chunks and testing models..."
            ):

                progress = st.progress(0)

                data = run_benchmark(
                    question,
                    test_runs
                )

                progress.progress(100)

                st.session_state.benchmark_data = data

            st.success("Benchmark completed!")

        except Exception as error:

            st.error(str(error))


# ==========================================
# DISPLAY RESULTS
# ==========================================

data = st.session_state.benchmark_data


if data:

    st.divider()

    st.header("📊 Performance Dashboard")

    summary = data["summary"]

    successful_runs = sum(
        item["successful_runs"]
        for item in summary
    )

    # --------------------------------------
    # METRICS
    # --------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Models Tested",
        len(MODELS)
    )

    col2.metric(
        "Successful Runs",
        successful_runs
    )

    col3.metric(
        "Retrieval Time",
        f'{data["retrieval_time"]:.3f}s'
    )

    if data["fastest_model"]:

        col4.metric(
            "Fastest Model",
            data["fastest_model"]["model"].split("/")[-1],
            f'{data["fastest_model"]["average"]:.3f}s avg'
        )

    else:

        col4.metric(
            "Fastest Model",
            "None"
        )

    # --------------------------------------
    # CHART
    # --------------------------------------

    st.divider()

    st.subheader("⚡ Average Response Time")

    if summary:

        df = pd.DataFrame(summary)

        fig = px.bar(

            df,

            x="model",

            y="average",

            color="model",

            text="average",

            labels={
                "model": "Model",
                "average": "Average Time (seconds)"
            },

            template="plotly_dark"

        )

        fig.update_traces(
            texttemplate="%{text:.3f}s",
            textposition="outside"
        )

        fig.update_layout(
            showlegend=False,
            xaxis_title="",
            yaxis_title="Seconds"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.warning("No successful model runs.")

    # --------------------------------------
    # COMPARISON TABLE
    # --------------------------------------

    st.subheader("📋 Model Comparison")

    if summary:

        st.dataframe(

            pd.DataFrame(summary),

            use_container_width=True,

            hide_index=True

        )

    # --------------------------------------
    # MODEL ANSWERS
    # --------------------------------------

    st.divider()

    st.header("💬 Model Answers")

    for result in data["results"]:

        title = (
            f'{result["model"]} | '
            f'Run {result["run"]}'
        )

        with st.expander(title):

            if result["status"] == "Success":

                st.success(
                    f'Response time: '
                    f'{result["response_time_seconds"]:.3f}s'
                )

                st.markdown("### Generated Answer")

                st.write(result["answer"])

            else:

                st.error("Model request failed")

                st.code(result["error"])

    # --------------------------------------
    # RETRIEVED CHUNKS
    # --------------------------------------

    st.divider()

    st.header("📚 Retrieved Context")

    st.write(
        f'Total retrieval time: '
        f'{data["retrieval_time"]:.3f} seconds'
    )

    for chunk in data["chunks"]:

        with st.expander(
            f'Chunk ID: {chunk["id"]}'
        ):

            st.write(chunk["text"])

            if "distance" in chunk:

                st.caption(
                    f'Distance: {chunk["distance"]:.4f}'
                )

    # --------------------------------------
    # FASTEST MODEL
    # --------------------------------------

    st.divider()

    st.header("🏆 Fastest Model")

    if data["fastest_model"]:

        winner = data["fastest_model"]

        st.success(
            f'Fastest average model: {winner["model"]}'
        )

        st.metric(
            "Average Response Time",
            f'{winner["average"]:.3f} seconds'
        )

        st.caption(
            f'Successful runs: '
            f'{winner["successful_runs"]}/'
            f'{winner["total_runs"]}'
        )

    else:

        st.warning(
            "No model completed successfully."
        )

    # --------------------------------------
    # CSV DOWNLOAD
    # --------------------------------------

    st.divider()

    st.header("📥 Export Results")

    if CSV_PATH.exists():

        with CSV_PATH.open("rb") as file:

            st.download_button(

                label="Download Benchmark CSV",

                data=file.read(),

                file_name="model_speed_results.csv",

                mime="text/csv"

            )


# ==========================================
# PREVIOUS BENCHMARK HISTORY
# ==========================================

st.divider()

st.header("📜 Benchmark History")

if CSV_PATH.exists():

    history = pd.read_csv(CSV_PATH)

    st.dataframe(
        history,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info("No benchmark history available yet.")


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "RAG Model Benchmark | OpenRouter + ChromaDB | "
    "Built with Streamlit"
)
