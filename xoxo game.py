import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import re
from datetime import datetime
import os

# --- 1. DATABASE SETUP WITH PROPER PERSISTENCE ---
DB_FILE = 'userdata.db'

def get_connection():
    """Create a new connection for each operation"""
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    """Initialize database tables if they don't exist"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS userstable(email TEXT PRIMARY KEY, password TEXT, currency TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS expensestable(id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, item TEXT, cost REAL, date TEXT)')
    conn.commit()
    conn.close()

# Initialize database
init_db()

# --- 2. SECURITY FUNCTIONS ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.fullmatch(regex, email)

def login_user(email, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM userstable WHERE email =? AND password =?', (email, password))
    result = c.fetchone()
    conn.close()
    return result

def create_user(email, password, currency):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO userstable(email, password, currency) VALUES (?,?,?)', 
                  (email, password, currency))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def update_currency(email, currency):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE userstable SET currency = ? WHERE email = ?', (currency, email))
    conn.commit()
    conn.close()

def add_expense(email, item, cost, date):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO expensestable(email, item, cost, date) VALUES (?,?,?,?)', 
              (email, item, cost, date))
    conn.commit()
    conn.close()

def get_expenses(email):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, item, cost, date FROM expensestable WHERE email =? ORDER BY id DESC', (email,))
    result = c.fetchall()
    conn.close()
    return result

def delete_expense(email, item):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM expensestable WHERE email=? AND item=? AND id IN (SELECT id FROM expensestable WHERE email=? AND item=? ORDER BY id DESC LIMIT 1)', 
              (email, item, email, item))
    conn.commit()
    conn.close()

# --- 3. APP CONFIGURATION ---
st.set_page_config(page_title="Expense Hero | Private Tracker", page_icon="💰", layout="centered")

# Initialize Session States
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'currency' not in st.session_state:
    st.session_state.currency = "$"

# --- 4. SIDEBAR (LOGIN & REGISTRATION) ---
st.sidebar.title("🔐 Secure Access")

if not st.session_state.logged_in:
    auth_mode = st.sidebar.radio("Choose Action:", ["Login", "Register"])
    email_input = st.sidebar.text_input("Email")
    pass_input = st.sidebar.text_input("Password", type="password")

    if auth_mode == "Login":
        if st.sidebar.button("Log In", use_container_width=True):
            if email_input and pass_input:
                user_data = login_user(email_input, make_hashes(pass_input))
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.user_email = user_data[0]
                    st.session_state.currency = user_data[2] if user_data[2] else "$"
                    st.sidebar.success("Login successful!")
                    st.rerun()
                else:
                    st.sidebar.error("❌ Invalid Email/Password")
            else:
                st.sidebar.warning("Please enter both email and password")
    else:
        if st.sidebar.button("Create Account", use_container_width=True):
            if not email_input or not pass_input:
                st.sidebar.warning("Please fill in all fields")
            elif not check_email(email_input):
                st.sidebar.error("❌ Please enter a valid email address")
            elif len(pass_input) < 4:
                st.sidebar.error("❌ Password must be at least 4 characters")
            else:
                success = create_user(email_input, make_hashes(pass_input), "$")
                if success:
                    st.sidebar.success("✅ Account Created! Please switch to Login.")
                else:
                    st.sidebar.error("❌ This email is already registered.")
else:
    st.sidebar.success(f"✅ Logged in as: {st.session_state.user_email}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.currency = "$"
        st.rerun()

# --- 5. MAIN PAGE CONTENT ---
if st.session_state.logged_in:
    st.title(f"💰 My Expense Log")
    
    # Currency Selector
    currencies = ["$", "₹", "£", "€", "¥", "₱", "RM", "AED", "SAR"]
    current_index = currencies.index(st.session_state.currency) if st.session_state.currency in currencies else 0
    new_curr = st.selectbox("Select Your Currency:", currencies, index=current_index)
    
    # Save currency preference if changed
    if new_curr != st.session_state.currency:
        update_currency(st.session_state.user_email, new_curr)
        st.session_state.currency = new_curr
        st.success(f"Currency updated to {new_curr}")
        st.rerun()

    # Fast Entry Form
    st.write("### Add New Entry")
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            item_name = st.text_input("Item Name (e.g. Lunch)", key="item_input")
        with col2:
            item_cost = st.number_input("Cost", min_value=0.0, step=0.01, key="cost_input")
        
        submit_button = st.form_submit_button("💾 Save Item", use_container_width=True)
        
        if submit_button:
            if not item_name:
                st.error("Please enter an item name")
            elif item_cost <= 0:
                st.error("Please enter a cost greater than 0")
            else:
                today = datetime.now().strftime("%Y-%m-%d")
                add_expense(st.session_state.user_email, item_name, item_cost, today)
                st.success(f"✅ Saved: {item_name} - {st.session_state.currency}{item_cost:.2f}")
                st.rerun()

    # Display Spending History
    st.write("---")
    history = get_expenses(st.session_state.user_email)

    if history:
        df = pd.DataFrame(history, columns=["ID", "Item", "Cost", "Date"])
        
        # Summary
        total = df['Cost'].sum()
        avg = df['Cost'].mean()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Spent", f"{st.session_state.currency} {total:,.2f}")
        with col2:
            st.metric("Total Items", len(df))
        with col3:
            st.metric("Average Cost", f"{st.session_state.currency} {avg:,.2f}")
        
        # Table
        st.write("### Your Recent Items")
        display_df = df[["Item", "Cost", "Date"]].copy()
        display_df['Cost'] = display_df['Cost'].apply(lambda x: f"{st.session_state.currency} {x:.2f}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Simple Chart
        st.write("### Spending Breakdown")
        chart_df = df.groupby('Item')['Cost'].sum().reset_index()
        st.bar_chart(chart_df.set_index('Item'))

        # Delete Option
        with st.expander("🗑️ Delete an Item"):
            delete_item = st.selectbox("Select item to remove:", df['Item'].unique())
            if st.button("🗑️ Delete Selected", type="primary"):
                delete_expense(st.session_state.user_email, delete_item)
                st.success(f"Removed: {delete_item}")
                st.rerun()
    else:
        st.info("📝 Your list is empty. Start adding items above!")

else:
    # PUBLIC HOME PAGE
    st.title("💰 Global Expense Hero")
    st.subheader("The fastest way to track your daily spending.")
    
    st.markdown("""
    Welcome to a simple, private way to manage your money. 
    
    ### ✨ Features
    * **🔒 Personal Accounts:** Every user's data is private and secure
    * **💱 Any Currency:** Works with USD, INR, EUR, and more
    * **📊 Visual Reports:** See your spending patterns at a glance
    * **🚀 Fast & Simple:** No ads, no clutter, just tracking
    
    ### 🎯 Get Started
    **Please Login or Register using the sidebar to begin tracking your expenses!**
    """)
    
    # Show sample data
    st.write("### 👀 Preview")
    sample_data = pd.DataFrame({
        'Item': ['Lunch', 'Coffee', 'Groceries', 'Transport'],
        'Cost': [15.50, 4.50, 45.00, 8.00],
        'Date': ['2024-01-01', '2024-01-01', '2024-01-02', '2024-01-02']
    })
    st.dataframe(sample_data, use_container_width=True, hide_index=True)

st.write("---")
st.caption("© 2024 Expense Hero | Privacy-First Finance | 🔒 Your data is stored locally and securely")
