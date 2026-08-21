import os
import requests
import streamlit as st
import pandas as pd


# =========================================================
# PAGE SETTINGS
# =========================================================

st.set_page_config(
    page_title="Personal Finance Tracker AI",
    page_icon="💰",
    layout="wide"
)


# =========================================================
# FILE STORAGE
# =========================================================

DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "transactions.csv")

os.makedirs(DATA_DIR, exist_ok=True)

# IMPORTANT:
# ID is now part of the official transaction structure.
columns = [
    "ID",
    "Date",
    "Description",
    "Amount",
    "Type",
    "Category"
]


# =========================================================
# CATEGORIES
# =========================================================

categories = [
    "Food",
    "Transport",
    "Bills",
    "Shopping",
    "Entertainment",
    "Health",
    "Education",
    "Salary",
    "Other"
]


# =========================================================
# SAVE TRANSACTIONS
# =========================================================

def save_transactions(df):

    df_to_save = df.copy()

    # Make sure all required columns exist.
    for column in columns:
        if column not in df_to_save.columns:
            df_to_save[column] = ""

    # Keep only the correct columns and order.
    df_to_save = df_to_save[columns]

    # Clean ID.
    df_to_save["ID"] = pd.to_numeric(
        df_to_save["ID"],
        errors="coerce"
    )

    df_to_save["ID"] = (
        df_to_save["ID"]
        .fillna(0)
        .astype(int)
    )

    # Clean dates.
    df_to_save["Date"] = pd.to_datetime(
        df_to_save["Date"],
        errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    # Clean amount.
    df_to_save["Amount"] = pd.to_numeric(
        df_to_save["Amount"],
        errors="coerce"
    ).fillna(0.0)

    # Clean text fields.
    df_to_save["Description"] = (
        df_to_save["Description"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df_to_save["Type"] = (
        df_to_save["Type"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df_to_save["Category"] = (
        df_to_save["Category"]
        .fillna("Other")
        .astype(str)
        .str.strip()
    )

    df_to_save.to_csv(
        DATA_FILE,
        index=False
    )


# =========================================================
# GET NEXT TRANSACTION ID
# =========================================================

def get_next_id(df):

    if df is None or df.empty:
        return 1

    ids = pd.to_numeric(
        df["ID"],
        errors="coerce"
    ).dropna()

    if ids.empty:
        return 1

    return int(ids.max()) + 1


# =========================================================
# LOAD TRANSACTIONS
# =========================================================

def load_transactions():

    if not os.path.exists(DATA_FILE):

        return pd.DataFrame(
            columns=columns
        )

    try:

        df = pd.read_csv(
            DATA_FILE
        )

        original_df = df.copy()

        # -------------------------------------------------
        # MAKE SURE ALL COLUMNS EXIST
        # -------------------------------------------------

        for column in columns:

            if column not in df.columns:

                df[column] = ""

        df = df[columns]

        # -------------------------------------------------
        # CLEAN ID
        # -------------------------------------------------

        df["ID"] = pd.to_numeric(
            df["ID"],
            errors="coerce"
        )

        # -------------------------------------------------
        # CLEAN DATE
        # -------------------------------------------------

        df["Date"] = pd.to_datetime(
            df["Date"],
            errors="coerce"
        ).dt.date

        # -------------------------------------------------
        # CLEAN AMOUNT
        # -------------------------------------------------

        df["Amount"] = pd.to_numeric(
            df["Amount"],
            errors="coerce"
        ).fillna(0.0)

        # -------------------------------------------------
        # CLEAN DESCRIPTION
        # -------------------------------------------------

        df["Description"] = (
            df["Description"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        # -------------------------------------------------
        # CLEAN TYPE
        # -------------------------------------------------

        df["Type"] = (
            df["Type"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        # Normalize type capitalization.
        df["Type"] = df["Type"].replace(
            {
                "income": "Income",
                "INCOME": "Income",
                "expense": "Expense",
                "EXPENSE": "Expense"
            }
        )

        # -------------------------------------------------
        # CLEAN CATEGORY
        # -------------------------------------------------

        df["Category"] = (
            df["Category"]
            .fillna("Other")
            .astype(str)
            .str.strip()
        )

        # -------------------------------------------------
        # REMOVE CORRUPTED / EMPTY ROWS
        # -------------------------------------------------
        #
        # Your screenshot shows rows like:
        #
        # 7,2026-08-20,,0.0,Income,Food
        # 8,2026-08-20,,0.0,Income,Food
        #
        # These are invalid because the application
        # requires a description and amount > 0.
        #
        # We remove those old accidental rows here.

        valid_rows = (
            (df["Description"] != "")
            &
            (df["Amount"] > 0)
            &
            (df["Type"].isin(["Income", "Expense"]))
        )

        df = df[valid_rows].copy()

        # -------------------------------------------------
        # FIX / CREATE IDS
        # -------------------------------------------------

        used_ids = set()

        valid_ids = pd.to_numeric(
            df["ID"],
            errors="coerce"
        )

        next_id = 1

        if not valid_ids.dropna().empty:

            next_id = int(
                valid_ids.dropna().max()
            ) + 1

        new_ids = []

        for value in df["ID"]:

            try:

                current_id = int(value)

            except (ValueError, TypeError):

                current_id = 0

            if current_id <= 0 or current_id in used_ids:

                while next_id in used_ids:
                    next_id += 1

                current_id = next_id
                next_id += 1

            used_ids.add(current_id)

            new_ids.append(current_id)

        df["ID"] = new_ids

        # -------------------------------------------------
        # RESET INDEX
        # -------------------------------------------------

        df = df.reset_index(
            drop=True
        )

        # -------------------------------------------------
        # SAVE CLEANED DATA
        # -------------------------------------------------

        changed = not df.equals(
            original_df.reindex(
                columns=columns
            ).reset_index(drop=True)
        )

        if changed:

            save_transactions(df)

        return df

    except Exception as e:

        st.error(
            f"Could not load transaction data: {e}"
        )

        return pd.DataFrame(
            columns=columns
        )


# =========================================================
# STEP 6
# VERIFIED FINANCIAL CALCULATIONS
# =========================================================

def calculate_financial_facts(df):

    if df is None or df.empty:

        return {
            "total_income": 0.0,
            "total_expenses": 0.0,
            "balance": 0.0,
            "expense_by_category": pd.Series(
                dtype=float
            ),
            "income_by_category": pd.Series(
                dtype=float
            ),
            "expense_count": 0,
            "income_count": 0
        }

    working_df = df.copy()

    working_df["Amount"] = pd.to_numeric(
        working_df["Amount"],
        errors="coerce"
    ).fillna(0.0)

    working_df["Type"] = (
        working_df["Type"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    working_df["Category"] = (
        working_df["Category"]
        .fillna("Other")
        .astype(str)
        .str.strip()
    )

    # -----------------------------------------------------
    # INCOME
    # -----------------------------------------------------

    income_df = working_df[
        working_df["Type"].str.lower() == "income"
    ]

    total_income = float(
        income_df["Amount"].sum()
    )

    # -----------------------------------------------------
    # EXPENSES
    # -----------------------------------------------------

    expense_df = working_df[
        working_df["Type"].str.lower() == "expense"
    ]

    total_expenses = float(
        expense_df["Amount"].sum()
    )

    # -----------------------------------------------------
    # BALANCE
    # -----------------------------------------------------

    balance = (
        total_income
        - total_expenses
    )

    # -----------------------------------------------------
    # EXPENSES BY CATEGORY
    # -----------------------------------------------------

    if not expense_df.empty:

        expense_by_category = (
            expense_df
            .groupby("Category")["Amount"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

    else:

        expense_by_category = pd.Series(
            dtype=float
        )

    # -----------------------------------------------------
    # INCOME BY CATEGORY
    # -----------------------------------------------------

    if not income_df.empty:

        income_by_category = (
            income_df
            .groupby("Category")["Amount"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

    else:

        income_by_category = pd.Series(
            dtype=float
        )

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": balance,
        "expense_by_category": expense_by_category,
        "income_by_category": income_by_category,
        "expense_count": len(expense_df),
        "income_count": len(income_df)
    }


# =========================================================
# STEP 6
# PREPARE VERIFIED AI DATA
# =========================================================

def prepare_ai_data(df):

    if df is None or df.empty:

        return (
            "NO TRANSACTIONS FOUND.\n\n"
            "There are currently no transactions "
            "in the selected data."
        )

    facts = calculate_financial_facts(df)

    total_income = facts["total_income"]
    total_expenses = facts["total_expenses"]
    balance = facts["balance"]

    expense_by_category = (
        facts["expense_by_category"]
    )

    income_by_category = (
        facts["income_by_category"]
    )

    # -----------------------------------------------------
    # HIGHEST EXPENSE CATEGORY
    # -----------------------------------------------------

    if not expense_by_category.empty:

        highest_category = (
            expense_by_category.index[0]
        )

        highest_amount = float(
            expense_by_category.iloc[0]
        )

        total_expense_amount = float(
            expense_by_category.sum()
        )

        if total_expense_amount > 0:

            highest_percentage = (
                highest_amount
                / total_expense_amount
                * 100
            )

        else:

            highest_percentage = 0.0

    else:

        highest_category = "None"
        highest_amount = 0.0
        highest_percentage = 0.0

    # -----------------------------------------------------
    # CATEGORY SUMMARY
    # -----------------------------------------------------

    if not expense_by_category.empty:

        category_lines = []

        for category, amount in (
            expense_by_category.items()
        ):

            category_lines.append(
                f"- {category}: ₹{float(amount):,.2f}"
            )

        expense_category_text = "\n".join(
            category_lines
        )

    else:

        expense_category_text = (
            "No expense categories found."
        )

    # -----------------------------------------------------
    # INCOME SUMMARY
    # -----------------------------------------------------

    if not income_by_category.empty:

        income_lines = []

        for category, amount in (
            income_by_category.items()
        ):

            income_lines.append(
                f"- {category}: ₹{float(amount):,.2f}"
            )

        income_category_text = "\n".join(
            income_lines
        )

    else:

        income_category_text = (
            "No income categories found."
        )

    # -----------------------------------------------------
    # TRANSACTIONS
    # -----------------------------------------------------

    transaction_df = df.copy()

    transaction_df["Amount"] = pd.to_numeric(
        transaction_df["Amount"],
        errors="coerce"
    ).fillna(0.0)

    transaction_text = transaction_df[
        columns
    ].to_string(
        index=False
    )

    # -----------------------------------------------------
    # VERIFIED FINANCIAL DATA
    # -----------------------------------------------------

    financial_data = f"""
VERIFIED FINANCIAL FACTS

These numbers were calculated by the application.
They are authoritative.

Total Income: ₹{total_income:,.2f}

Total Expenses: ₹{total_expenses:,.2f}
t.sub
Current Balance: ₹{balance:,.2f}

Number of Income Transactions: {facts["income_count"]}

Number of Expense Transactions: {facts["expense_count"]}

HIGHEST EXPENSE CATEGORY

Category: {highest_category}
Amount: ₹{highest_amount:,.2f}
Share of Expenses: {highest_percentage:.1f}%

EXPENSES BY ACTUAL CATEGORY

{expense_category_text}

INCOME BY ACTUAL CATEGORY

{income_category_text}

TRANSACTIONS

{transaction_text}
"""

    return financial_data


# =========================================================
# LOCAL AI - OLLAMA
# =========================================================

def ask_local_ai(question, financial_data):

    # IMPORTANT:
    # This must be a real URL, not a Markdown link.
    url = "http://localhost:11434/api/generate"

    prompt = f"""
You are a personal finance assistant.

You are given VERIFIED financial calculations
created by the application.

IMPORTANT RULES:

1. Use the verified financial facts as the source
   of truth.

2. Do NOT recalculate totals differently.

3. Do NOT invent transactions.

4. Do NOT invent categories.

5. Do NOT invent amounts.

6. Do NOT assume transactions that are not listed.

7. The Category column is the actual transaction category.

8. The Description column is ONLY a description.

9. Never treat a word from Description as a category.

Example:

Category = Food
Description = Groceries

This means:

Category = Food
Description = Groceries

It does NOT mean that Groceries is a separate category.

10. When the user asks:

"Where am I spending the most?"

Answer using:

HIGHEST EXPENSE CATEGORY

Use the category and amount already calculated
by the application.

11. When the user asks:

"What is my biggest expense?"

Use the verified highest expense category.

12. When the user asks:

"How much did I spend on Food?"

Use the verified expense category summary.

13. When the user asks:

"How much did I spend?"

Use Total Expenses.

14. When the user asks:

"How much income did I receive?"

Use Total Income.

15. When the user asks:

"What is my balance?"

Use Current Balance.

16. If there is no data needed to answer a question,
clearly say that the required data is not available.

17. Keep the answer concise and easy to understand.

18. Always use ₹ for Indian currency.

19. When useful, show a short calculation or explanation.

VERIFIED FINANCIAL DATA:

{financial_data}

USER QUESTION:

{question}

Answer the user's question using the verified data above.
"""

    payload = {
        "model": "llama3.2:3b",
        "prompt": prompt,
        "stream": False
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=120
        )

        response.raise_for_status()

        result = response.json()

        ai_response = result.get(
            "response",
            ""
        )

        if not ai_response.strip():

            return (
                "The AI did not return a response."
            )

        return ai_response.strip()

    except requests.exceptions.ConnectionError:

        return (
            "❌ Could not connect to Ollama.\n\n"
            "Please make sure Ollama is running."
        )

    except requests.exceptions.Timeout:

        return (
            "❌ Ollama took too long to respond. "
            "Please try again."
        )

    except Exception as e:

        return f"❌ AI error: {e}"


# =========================================================
# INITIALIZE SESSION STATE
# =========================================================

if "transactions" not in st.session_state:

    st.session_state.transactions = (
        load_transactions()
    )


if "transaction_form_reset" not in st.session_state:

    st.session_state.transaction_form_reset = 0


# =========================================================
# TITLE
# =========================================================

st.title(
    "💰 Personal Finance Tracker AI"
)

st.write(
    "Track your income, expenses, savings, "
    "and financial health in one place."
)


# =========================================================
# ADD TRANSACTION
# =========================================================

st.subheader(
    "➕ Add a Transaction"
)


form_key = (
    f"transaction_form_"
    f"{st.session_state.transaction_form_reset}"
)


with st.form(form_key):

    col1, col2 = st.columns(2)

    # -----------------------------------------------------
    # LEFT COLUMN
    # -----------------------------------------------------

    with col1:

        date = st.date_input(
            "Date",
            value=pd.Timestamp.today().date()
        )

        description = st.text_input(
            "Description",
            placeholder=(
                "e.g. Groceries, Salary, Rent"
            )
        )

        category = st.selectbox(
            "Category",
            categories
        )

    # -----------------------------------------------------
    # RIGHT COLUMN
    # -----------------------------------------------------

    with col2:

        amount = st.number_input(
            "Amount (₹)",
            min_value=0.0,
            step=100.0,
            format="%.2f"
        )

        transaction_type = st.selectbox(
            "Type",
            [
                "Income",
                "Expense"
            ]
        )

    submitted = st.form_submit_button(
        "Add Transaction",
        use_container_width=True
    )

    # -----------------------------------------------------
    # SAVE TRANSACTION
    # -----------------------------------------------------

    if submitted:

        if not description.strip():

            st.error(
                "Please enter a description."
            )

        elif amount <= 0:

            st.error(
                "Amount must be greater than ₹0."
            )

        else:

            # IMPORTANT:
            # Generate ID from existing maximum ID.
            new_id = get_next_id(
                st.session_state.transactions
            )

            new_transaction = pd.DataFrame(
                [
                    {
                        "ID": new_id,
                        "Date": date,
                        "Description": description.strip(),
                        "Amount": float(amount),
                        "Type": transaction_type,
                        "Category": category
                    }
                ]
            )

            st.session_state.transactions = (
                pd.concat(
                    [
                        st.session_state.transactions,
                        new_transaction
                    ],
                    ignore_index=True
                )
            )

            save_transactions(
                st.session_state.transactions
            )

            # Create a completely new form.
            st.session_state.transaction_form_reset += 1

            st.success(
                f"✅ Transaction #{new_id} added and saved permanently!"
            )

            st.rerun()


# =========================================================
# SEARCH & FILTERS
# =========================================================

st.divider()

st.subheader(
    "🔎 Search & Filters"
)


df_all = (
    st.session_state.transactions.copy()
)


# =========================================================
# MONTH OPTIONS
# =========================================================

month_options = [
    "All Months"
]

if not df_all.empty:

    temp_dates = pd.to_datetime(
        df_all["Date"],
        errors="coerce"
    )

    valid_months = (
        temp_dates
        .dropna()
        .dt.to_period("M")
        .astype(str)
        .drop_duplicates()
        .sort_values(
            ascending=False
        )
        .tolist()
    )

    month_options.extend(
        valid_months
    )


# =========================================================
# FILTER SESSION STATE
# =========================================================

if "search_filter" not in st.session_state:
    st.session_state.search_filter = ""

if "month_filter" not in st.session_state:
    st.session_state.month_filter = "All Months"

if "type_filter" not in st.session_state:
    st.session_state.type_filter = "All Types"

if "category_filter" not in st.session_state:
    st.session_state.category_filter = (
        "All Categories"
    )


# =========================================================
# DEFAULT DATE FILTERS
# =========================================================

if "start_date_filter" not in st.session_state:

    if not df_all.empty:

        valid_dates = pd.to_datetime(
            df_all["Date"],
            errors="coerce"
        ).dropna()

        if not valid_dates.empty:

            st.session_state.start_date_filter = (
                valid_dates.min().date()
            )

        else:

            st.session_state.start_date_filter = (
                pd.Timestamp.today().date()
            )

    else:

        st.session_state.start_date_filter = (
            pd.Timestamp.today().date()
        )


if "end_date_filter" not in st.session_state:

    if not df_all.empty:

        valid_dates = pd.to_datetime(
            df_all["Date"],
            errors="coerce"
        ).dropna()

        if not valid_dates.empty:

            st.session_state.end_date_filter = (
                valid_dates.max().date()
            )

        else:

            st.session_state.end_date_filter = (
                pd.Timestamp.today().date()
            )

    else:

        st.session_state.end_date_filter = (
            pd.Timestamp.today().date()
        )


# =========================================================
# CLEAR FILTERS
# =========================================================

if st.button(
    "🔄 Clear Filters",
    use_container_width=True
):

    st.session_state.search_filter = ""
    st.session_state.month_filter = (
        "All Months"
    )
    st.session_state.type_filter = (
        "All Types"
    )
    st.session_state.category_filter = (
        "All Categories"
    )

    if not df_all.empty:

        valid_dates = pd.to_datetime(
            df_all["Date"],
            errors="coerce"
        ).dropna()

        if not valid_dates.empty:

            st.session_state.start_date_filter = (
                valid_dates.min().date()
            )

            st.session_state.end_date_filter = (
                valid_dates.max().date()
            )

        else:

            today = pd.Timestamp.today().date()

            st.session_state.start_date_filter = today
            st.session_state.end_date_filter = today

    else:

        today = pd.Timestamp.today().date()

        st.session_state.start_date_filter = today
        st.session_state.end_date_filter = today

    st.rerun()


# =========================================================
# FILTER CONTROLS
# =========================================================

filter_col1, filter_col2 = st.columns(2)


with filter_col1:

    search_text = st.text_input(
        "🔎 Search",
        placeholder="Search description...",
        key="search_filter"
    )


with filter_col2:

    if (
        st.session_state.month_filter
        not in month_options
    ):

        st.session_state.month_filter = (
            "All Months"
        )

    selected_month = st.selectbox(
        "📅 Month",
        month_options,
        key="month_filter"
    )


# =========================================================
# TYPE & CATEGORY
# =========================================================

filter_col3, filter_col4 = st.columns(2)


with filter_col3:

    selected_type = st.selectbox(
        "💰 Type",
        [
            "All Types",
            "Income",
            "Expense"
        ],
        key="type_filter"
    )


with filter_col4:

    category_options = (
        ["All Categories"]
        + categories
    )

    selected_category = st.selectbox(
        "🏷️ Category",
        category_options,
        key="category_filter"
    )


# =========================================================
# CUSTOM DATE RANGE
# =========================================================

st.markdown(
    "### 📅 Custom Date Range"
)


date_col1, date_col2 = st.columns(2)


with date_col1:

    start_date = st.date_input(
        "Start Date",
        key="start_date_filter"
    )


with date_col2:

    end_date = st.date_input(
        "End Date",
        key="end_date_filter"
    )


# =========================================================
# APPLY FILTERS
# =========================================================

if start_date > end_date:

    st.error(
        "⚠️ Start Date cannot be after End Date."
    )

    filtered_df = pd.DataFrame(
        columns=df_all.columns
    )

else:

    filtered_df = df_all.copy()

    # -----------------------------------------------------
    # SEARCH
    # -----------------------------------------------------

    if search_text.strip():

        search_value = (
            search_text
            .strip()
            .lower()
        )

        filtered_df = filtered_df[
            filtered_df["Description"]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.contains(
                search_value,
                na=False
            )
        ]

    # -----------------------------------------------------
    # MONTH
    # -----------------------------------------------------

    if selected_month != "All Months":

        filtered_dates = pd.to_datetime(
            filtered_df["Date"],
            errors="coerce"
        )

        filtered_df = filtered_df[
            filtered_dates
            .dt.to_period("M")
            .astype(str)
            == selected_month
        ]

    # -----------------------------------------------------
    # TYPE
    # -----------------------------------------------------

    if selected_type != "All Types":

        filtered_df = filtered_df[
            filtered_df["Type"]
            == selected_type
        ]

    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    if selected_category != "All Categories":

        filtered_df = filtered_df[
            filtered_df["Category"]
            == selected_category
        ]

    # -----------------------------------------------------
    # DATE RANGE
    # -----------------------------------------------------

    filtered_dates = pd.to_datetime(
        filtered_df["Date"],
        errors="coerce"
    ).dt.date

    filtered_df = filtered_df[
        filtered_dates.between(
            start_date,
            end_date
        )
    ]


# =========================================================
# FILTER RESULT
# =========================================================

if not df_all.empty:

    st.caption(
        f"Showing {len(filtered_df)} of "
        f"{len(df_all)} transactions."
    )

else:

    st.info(
        "No transactions have been added yet."
    )


# =========================================================
# DASHBOARD CALCULATIONS
# =========================================================

df = filtered_df.copy()


if not df.empty:

    df["Amount"] = pd.to_numeric(
        df["Amount"],
        errors="coerce"
    ).fillna(0.0)

    total_income = df.loc[
        df["Type"] == "Income",
        "Amount"
    ].sum()

    total_expenses = df.loc[
        df["Type"] == "Expense",
        "Amount"
    ].sum()

    balance = (
        total_income
        - total_expenses
    )

else:

    total_income = 0.0
    total_expenses = 0.0
    balance = 0.0


# =========================================================
# DASHBOARD
# =========================================================

st.divider()

st.subheader(
    "📊 Dashboard"
)


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "💰 Total Income",
        f"₹{total_income:,.2f}"
    )

with col2:
    st.metric(
        "💸 Total Expenses",
        f"₹{total_expenses:,.2f}"
    )

with col3:
    st.metric(
        "💵 Balance",
        f"₹{balance:,.2f}"
    )

with col4:

    if total_income > 0:
        savings_rate = (balance / total_income) * 100
    else:
        savings_rate = 0

    st.metric(
        "📈 Savings Rate",
        f"{savings_rate:.1f}%"
    )


# =========================================================
# FINANCIAL HEALTH
# =========================================================

st.subheader(
    "💡 Financial Health"
)


if total_income > 0:

    savings_rate = (
        balance / total_income
    ) * 100

    expense_ratio = (
        total_expenses / total_income
    ) * 100

    # Financial health score
    if savings_rate >= 30:
        health_score = 100
        health_status = "🟢 Excellent financial condition"

    elif savings_rate >= 20:
        health_score = 90
        health_status = "🟢 Very good financial condition"

    elif savings_rate >= 10:
        health_score = 75
        health_status = "🟡 Good, but there is room to improve"

    elif savings_rate >= 0:
        health_score = 50
        health_status = "🟠 Needs improvement"

    else:
        health_score = 20
        health_status = "🔴 Expenses are higher than income"


    # Health score
    st.metric(
        "🏆 Financial Health Score",
        f"{health_score}/100"
    )

    st.write(
        f"**{health_status}**"
    )


    # Financial indicators
    health_col1, health_col2 = st.columns(2)


    with health_col1:

        st.metric(
            "📈 Savings Rate",
            f"{savings_rate:.1f}%"
        )


    with health_col2:

        st.metric(
            "💸 Expense Ratio",
            f"{expense_ratio:.1f}%"
        )


    # Recommendation
    if savings_rate >= 30:

        st.success(
            "Excellent! Your savings rate is strong. "
            "Continue maintaining this balance."
        )

    elif savings_rate >= 10:

        st.info(
            "Your finances are moving in a positive direction. "
            "Try to gradually increase your savings."
        )

    elif savings_rate >= 0:

        st.warning(
            "Your savings rate is low. "
            "Consider reviewing your expenses and finding areas to reduce spending."
        )

    else:

        st.error(
            "⚠️ Your expenses are higher than your income. "
            "Review your spending and prioritize essential expenses."
        )


elif total_expenses > 0:

    st.warning(
        "You currently have expenses but no income "
        "recorded in the selected filter."
    )


else:

    st.info(
        "Add transactions to see your financial health."
    )

# =========================================================
# FINANCIAL OVERVIEW
# =========================================================

if not df.empty:

    st.divider()

    st.subheader(
        "📈 Financial Overview"
    )

    chart_col1, chart_col2 = st.columns(2)

    # -----------------------------------------------------
    # INCOME VS EXPENSE
    # -----------------------------------------------------

    with chart_col1:

        st.caption(
            "Income vs Expenses"
        )

        summary = pd.DataFrame(
            {
                "Income": [total_income],
                "Expenses": [total_expenses]
            }
        )

        st.bar_chart(
            summary.T,
            height=350
        )

    # -----------------------------------------------------
    # EXPENSE BREAKDOWN
    # -----------------------------------------------------

    with chart_col2:

        st.caption(
            "Expenses by Category"
        )

        expenses_df = df[
            df["Type"] == "Expense"
        ]

        if not expenses_df.empty:

            expense_breakdown = (
                expenses_df
                .groupby("Category")["Amount"]
                .sum()
                .sort_values(
                    ascending=False
                )
            )

            st.bar_chart(
                expense_breakdown,
                height=350
            )

        else:

            st.info(
                "No expenses in the selected filter."
            )


# =========================================================
# SPENDING INSIGHTS
# =========================================================

if not df.empty:

    st.divider()

    st.subheader(
        "💡 Spending Insights"
    )

    insights_expenses = df[
        df["Type"] == "Expense"
    ].copy()

    if not insights_expenses.empty:

        insights_expenses["Amount"] = (
            pd.to_numeric(
                insights_expenses["Amount"],
                errors="coerce"
            ).fillna(0.0)
        )

        insight_total_expenses = (
            insights_expenses["Amount"].sum()
        )

        category_spending = (
            insights_expenses
            .groupby("Category")["Amount"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        highest_category = (
            category_spending.index[0]
        )

        highest_amount = (
            category_spending.iloc[0]
        )

        if insight_total_expenses > 0:

            highest_percentage = (
                highest_amount
                / insight_total_expenses
            ) * 100

        else:

            highest_percentage = 0.0

        insight_col1, insight_col2, insight_col3 = (
            st.columns(3)
        )

        with insight_col1:

            st.metric(
                "💸 Total Expenses",
                f"₹{insight_total_expenses:,.2f}"
            )

        with insight_col2:

            st.metric(
                "🏆 Highest Spending",
                highest_category
            )

        with insight_col3:

            st.metric(
                "📊 Highest Category Share",
                f"{highest_percentage:.1f}%"
            )

        st.markdown(
            "### 📊 Spending by Category"
        )

        category_insights = pd.DataFrame(
            {
                "Amount": category_spending
            }
        )

        if insight_total_expenses > 0:

            category_insights["Percentage"] = (
                category_insights["Amount"]
                / insight_total_expenses
                * 100
            )

        else:

            category_insights["Percentage"] = 0.0

        category_insights["Percentage"] = (
            category_insights["Percentage"]
            .round(1)
        )

        st.dataframe(
            category_insights,
            use_container_width=True
        )

        if highest_percentage >= 50:

            st.warning(
                f"⚠️ {highest_category} accounts for "
                f"{highest_percentage:.1f}% of your total "
                f"expenses. This is your biggest spending "
                f"area, so reducing it could have a strong "
                f"impact on your savings."
            )

        elif highest_percentage >= 30:

            st.info(
                f"💡 {highest_category} is your largest "
                f"expense category at "
                f"{highest_percentage:.1f}% of total "
                f"spending. Keep an eye on this category."
            )

        else:

            st.success(
                f"✅ Your spending is relatively spread "
                f"across categories. Your largest category "
                f"is {highest_category} at "
                f"{highest_percentage:.1f}%."
            )

        if total_income > 0:

            current_savings_rate = (
                balance
                / total_income
            ) * 100

            if current_savings_rate < 10:

                st.warning(
                    "💰 Your current savings rate is below "
                    "10%. Consider reviewing your largest "
                    "expense categories and reducing "
                    "non-essential spending."
                )

            elif current_savings_rate < 30:

                st.info(
                    "💰 Your savings rate is between 10% "
                    "and 30%. A small reduction in your "
                    "largest expenses could help you save "
                    "more."
                )

            else:

                st.success(
                    "💰 Great job! Your current savings "
                    "rate is 30% or higher."
                )

    else:

        st.info(
            "Add an expense to generate spending insights."
        )


# =========================================================
# MONTHLY SUMMARY
# =========================================================

if not df.empty:

    st.divider()

    st.subheader(
        "📅 Monthly Summary"
    )

    monthly_df = df.copy()

    monthly_df["Date"] = pd.to_datetime(
        monthly_df["Date"],
        errors="coerce"
    )

    monthly_df = monthly_df.dropna(
        subset=["Date"]
    )

    if not monthly_df.empty:

        monthly_df["Month"] = (
            monthly_df["Date"]
            .dt.to_period("M")
            .astype(str)
        )

        monthly_income = (
            monthly_df[
                monthly_df["Type"] == "Income"
            ]
            .groupby("Month")["Amount"]
            .sum()
        )

        monthly_expenses = (
            monthly_df[
                monthly_df["Type"] == "Expense"
            ]
            .groupby("Month")["Amount"]
            .sum()
        )

        monthly_summary = pd.DataFrame(
            {
                "Income": monthly_income,
                "Expenses": monthly_expenses
            }
        ).fillna(0)

        monthly_summary["Balance"] = (
            monthly_summary["Income"]
            - monthly_summary["Expenses"]
        )

        monthly_summary = (
            monthly_summary
            .sort_index(
                ascending=False
            )
        )

        st.dataframe(
            monthly_summary,
            use_container_width=True
        )


# =========================================================
# ALL / FILTERED TRANSACTIONS
# =========================================================

st.divider()

st.subheader(
    "📋 Transactions"
)


if not df.empty:

    display_df = df.copy()

    display_df = display_df.sort_values(
        "Date",
        ascending=False
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "No transactions match the selected filters."
    )


# =========================================================
# MANAGE TRANSACTIONS
# =========================================================

st.divider()

st.subheader(
    "✏️ Manage Transactions"
)


manage_df = (
    st.session_state.transactions.copy()
)


if not manage_df.empty:

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    manage_df = manage_df.sort_values(
        "Date",
        ascending=False
    )

    # -----------------------------------------------------
    # CREATE OPTIONS
    # -----------------------------------------------------

    transaction_options = []
    transaction_ids = []

    for _, row in manage_df.iterrows():

        date_value = row["Date"]

        if pd.isna(date_value):

            date_text = "Unknown date"

        else:

            date_text = str(date_value)

        label = (
            f"#{int(row['ID'])} | "
            f"{date_text} | "
            f"{row['Description']} | "
            f"₹{float(row['Amount']):,.2f} | "
            f"{row['Type']}"
        )

        transaction_options.append(
            label
        )

        transaction_ids.append(
            int(row["ID"])
        )

    # -----------------------------------------------------
    # SELECT TRANSACTION
    # -----------------------------------------------------

    selected_position = st.selectbox(
        "Select a transaction",
        range(
            len(transaction_options)
        ),
        format_func=lambda x:
            transaction_options[x],
        key="selected_transaction_position"
    )

    selected_id = (
        transaction_ids[
            selected_position
        ]
    )

    selected_rows = (
        st.session_state.transactions[
            st.session_state.transactions["ID"]
            == selected_id
        ]
    )

    if selected_rows.empty:

        st.error(
            "Selected transaction could not be found."
        )

    else:

        selected_transaction = (
            selected_rows.iloc[0].copy()
        )

        # =================================================
        # EDIT TRANSACTION
        # =================================================

        st.markdown(
            "### ✏️ Edit Selected Transaction"
        )

        edit_col1, edit_col2 = st.columns(2)

        edit_key = (
            f"edit_{selected_id}"
        )

        with edit_col1:

            try:

                edit_date_value = (
                    pd.to_datetime(
                        selected_transaction["Date"]
                    ).date()
                )

            except Exception:

                edit_date_value = (
                    pd.Timestamp.today().date()
                )

            edit_date = st.date_input(
                "Date",
                value=edit_date_value,
                key=f"{edit_key}_date"
            )

            edit_description = st.text_input(
                "Description",
                value=str(
                    selected_transaction[
                        "Description"
                    ]
                ),
                key=f"{edit_key}_description"
            )

            current_category = str(
                selected_transaction[
                    "Category"
                ]
            )

            if current_category not in categories:

                current_category = "Other"

            edit_category = st.selectbox(
                "Category",
                categories,
                index=categories.index(
                    current_category
                ),
                key=f"{edit_key}_category"
            )

        with edit_col2:

            edit_amount = st.number_input(
                "Amount (₹)",
                min_value=0.0,
                value=float(
                    selected_transaction[
                        "Amount"
                    ]
                ),
                step=100.0,
                format="%.2f",
                key=f"{edit_key}_amount"
            )

            current_type = str(
                selected_transaction["Type"]
            )

            if current_type not in [
                "Income",
                "Expense"
            ]:

                current_type = "Expense"

            edit_type = st.selectbox(
                "Type",
                [
                    "Income",
                    "Expense"
                ],
                index=[
                    "Income",
                    "Expense"
                ].index(
                    current_type
                ),
                key=f"{edit_key}_type"
            )

        # =================================================
        # SAVE CHANGES
        # =================================================

        if st.button(
            "💾 Save Changes",
            use_container_width=True,
            key=f"{edit_key}_save"
        ):

            if not edit_description.strip():

                st.error(
                    "Description cannot be empty."
                )

            elif edit_amount <= 0:

                st.error(
                    "Amount must be greater than ₹0."
                )

            else:

                matching_rows = (
                    st.session_state.transactions[
                        st.session_state.transactions["ID"]
                        == selected_id
                    ].index
                )

                if not matching_rows.empty:

                    row_index = matching_rows[0]

                    st.session_state.transactions.loc[
                        row_index,
                        "Date"
                    ] = edit_date

                    st.session_state.transactions.loc[
                        row_index,
                        "Description"
                    ] = edit_description.strip()

                    st.session_state.transactions.loc[
                        row_index,
                        "Amount"
                    ] = float(edit_amount)

                    st.session_state.transactions.loc[
                        row_index,
                        "Type"
                    ] = edit_type

                    st.session_state.transactions.loc[
                        row_index,
                        "Category"
                    ] = edit_category

                    save_transactions(
                        st.session_state.transactions
                    )

                    st.success(
                        f"✅ Transaction #{selected_id} updated successfully!"
                    )

                    st.rerun()

        # =================================================
        # DELETE TRANSACTION
        # =================================================

        st.markdown(
            "### 🗑️ Delete Transaction"
        )

        st.warning(
            f"You are about to delete transaction "
            f"#{selected_id}: "
            f"{selected_transaction['Description']} "
            f"— ₹{float(selected_transaction['Amount']):,.2f} "
            f"({selected_transaction['Type']})"
        )

        confirm_delete = st.checkbox(
            "I understand that this transaction "
            "will be permanently deleted.",
            key=f"{edit_key}_confirm_delete"
        )

        if st.button(
            "🗑️ Delete Selected Transaction",
            disabled=not confirm_delete,
            use_container_width=True,
            key=f"{edit_key}_delete"
        ):

            st.session_state.transactions = (
                st.session_state.transactions[
                    st.session_state.transactions["ID"]
                    != selected_id
                ]
                .reset_index(drop=True)
            )

            save_transactions(
                st.session_state.transactions
            )

            st.success(
                f"✅ Transaction #{selected_id} deleted successfully!"
            )

            st.rerun()

else:

    st.info(
        "There are no transactions to manage."
    )


# =========================================================
# AI FINANCIAL ADVISOR
# =========================================================

st.divider()

st.subheader(
    "🤖 AI Financial Advisor"
)

st.write(
    "Ask questions about your income, expenses, "
    "spending habits, and savings."
)


# =========================================================
# AI QUESTION
# =========================================================

ai_question = st.text_area(
    "💬 Ask your financial question",
    placeholder=(
        "Examples:\n"
        "• Where am I spending the most?\n"
        "• How can I save more money?\n"
        "• Analyze my expenses.\n"
        "• What is my biggest expense?\n"
        "• How much did I spend on Food?\n"
        "• How much income did I receive?\n"
        "• What is my current balance?"
    ),
    height=120,
    key="ai_question"
)


# =========================================================
# ASK AI
# =========================================================

if st.button(
    "🤖 Ask AI",
    use_container_width=True,
    key="ask_ai_button"
):

    if not ai_question.strip():

        st.warning(
            "Please enter a question first."
        )

    elif st.session_state.transactions.empty:

        st.info(
            "Add some transactions before asking "
            "the AI to analyze your finances."
        )

    else:

        with st.spinner(
            "🤖 Analyzing your finances..."
        ):

            # Use filtered_df so AI answers correspond
            # to the currently selected filters.
            financial_data = prepare_ai_data(
                filtered_df
            )

            ai_response = ask_local_ai(
                ai_question.strip(),
                financial_data
            )

        st.markdown(
            "### 🤖 AI Response"
        )

        st.write(
            ai_response
        )


# =========================================================
# DOWNLOAD DATA
# =========================================================

if not st.session_state.transactions.empty:

    st.divider()

    st.subheader(
        "📥 Export Data"
    )

    csv_data = (
        st.session_state.transactions
        .to_csv(index=False)
        .encode("utf-8")
    )

    st.download_button(
        label="Download Transactions CSV",
        data=csv_data,
        file_name=(
            "personal_finance_transactions.csv"
        ),
        mime="text/csv"
    )


# =========================================================
# DANGER ZONE
# =========================================================

st.divider()


with st.expander(
    "⚠️ Danger Zone"
):

    st.warning(
        "This will permanently delete "
        "all saved transactions."
    )

    confirm_delete_all = st.checkbox(
        "I understand that ALL transactions "
        "will be permanently deleted.",
        key="confirm_delete_all"
    )

    if st.button(
        "🗑️ Delete All Transactions",
        disabled=not confirm_delete_all
    ):

        st.session_state.transactions = (
            pd.DataFrame(
                columns=columns
            )
        )

        if os.path.exists(DATA_FILE):

            os.remove(DATA_FILE)

        st.success(
            "✅ All transactions have been deleted."
        )

        st.rerun()