import os
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

from agent import run_agent, log, SUPPORT_TRIGGERS
from database import get_connection
from tools import create_github_issue

load_dotenv()

st.set_page_config(
    page_title="Data Insights App",
    page_icon="🛒",
    layout="wide",
)

SAMPLE_QUERIES = [
    "Show top 5 products by sales",
    "Show monthly revenue trend",
    "Who are the top 5 most active customers?",
    "Show total revenue by category",
    "Show the last 10 orders",
]


def load_sidebar_stats() -> dict:
    conn = get_connection()
    stats = {
        "customers": conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
        "products": conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "orders": conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "revenue": conn.execute(
            "SELECT COALESCE(ROUND(SUM(total_amount), 2), 0) FROM orders WHERE status='delivered'"
        ).fetchone()[0],
    }
    conn.close()
    return stats


def load_category_chart() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status = 'delivered'
        GROUP BY p.category
        ORDER BY revenue DESC
        """,
        conn,
    )
    conn.close()
    return df


def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "show_ticket_form" not in st.session_state:
        st.session_state.show_ticket_form = False
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None


def render_sidebar() -> None:
    with st.sidebar:
        st.title("🛒 Data Insights")
        st.subheader("📊 Dataset Info")

        stats = load_sidebar_stats()
        col1, col2 = st.columns(2)
        col1.metric("Customers", stats["customers"])
        col2.metric("Products", stats["products"])
        col1.metric("Orders", stats["orders"])
        col2.metric("Revenue", f"${stats['revenue']:,.0f}")

        st.divider()
        st.subheader("📈 Revenue by Category")
        df = load_category_chart()
        if not df.empty:
            fig = px.bar(
                df, x="category", y="revenue", color="category",
                labels={"revenue": "Revenue ($)", "category": "Category"},
            )
            fig.update_layout(showlegend=False, margin=dict(t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.subheader("💡 Sample Queries")
        for q in SAMPLE_QUERIES:
            if st.button(q, use_container_width=True, key=f"sample_{q[:20]}"):
                st.session_state.pending_query = q
                st.rerun()


def render_ticket_form() -> None:
    st.divider()
    with st.expander("🎫 Support Ticket", expanded=st.session_state.show_ticket_form):
        last_user_msg = next(
            (m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"),
            "",
        )
        title = st.text_input(
            "Issue title",
            value=f"Support: {last_user_msg[:60]}",
            key="ticket_title",
        )
        body = st.text_area(
            "Description",
            value=f"User question: {last_user_msg}\n\nAdditional details: ",
            height=120,
            key="ticket_body",
        )
        if st.button("Create GitHub Issue", type="primary", key="create_ticket"):
            if not os.environ.get("GITHUB_TOKEN") or not os.environ.get("GITHUB_REPO"):
                st.error("GITHUB_TOKEN and GITHUB_REPO must be set in your .env file or HF Spaces secrets.")
            else:
                with st.spinner("Creating ticket..."):
                    try:
                        url = create_github_issue(title, body)
                        log("TICKET", f"GitHub issue created: {url}")
                        st.success(f"Ticket created: [View Issue]({url})")
                        st.session_state.show_ticket_form = False
                    except Exception as e:
                        st.error(f"Error: {e}")


def is_support_request(text: str) -> bool:
    return any(trigger in text.lower() for trigger in SUPPORT_TRIGGERS)


def main() -> None:
    init_session_state()
    render_sidebar()

    st.title("💬 Data Insights — Chat with your data")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if st.session_state.pending_query:
        user_input = st.session_state.pending_query
        st.session_state.pending_query = None
    else:
        user_input = st.chat_input("Ask a question about your data...")

    if user_input:
        log("USER", user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        if is_support_request(user_input):
            st.session_state.show_ticket_form = True

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = run_agent(list(st.session_state.messages))
            st.markdown(response)

        if "support ticket" in response.lower() or "github issue" in response.lower():
            st.session_state.show_ticket_form = True

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

    render_ticket_form()

    if not st.session_state.show_ticket_form:
        if st.button("🎫 Open Support Ticket", key="open_ticket_btn"):
            st.session_state.show_ticket_form = True
            st.rerun()


if __name__ == "__main__":
    main()
