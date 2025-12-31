import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import re
from datetime import datetime

# --- 1. DATABASE SETUP ---
# This creates a local database file to remember your users and their money
conn = sqlite3.connect('userdata.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS userstable(email TEXT UNIQUE, password TEXT, currency TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS expensestable(email TEXT, item TEXT, cost REAL, date TEXT)')
conn.commit()

# --- 2. SECURITY FUNCTIONS ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.fullmatch(regex, email)

def login_user(email, password):
    c.execute('SELECT * FROM userstable WHERE email =? AND password =?', (email, password))
    return c.fetchone()

# --- 3. APP CONFIGURATION ---
st.set_page_config(page_title="Expense Hero | Private Tracker", page_icon="💰", layout="centered")

# Initialize Session States (To keep you logged in while you click around)
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
                    st.rerun()
                else:
                    st.sidebar.error("Invalid Email/Password")
    else:
        if st.sidebar.button("Create Account", use_container_width=True):
            if check_email(email_input) and len(pass_input) >= 4:
                try:
                    c.execute('INSERT INTO userstable(email, password, currency) VALUES (?,?,?)', 
                              (email_input, make_hashes(pass_input), "$"))
                    conn.commit()
                    st.sidebar.success("Account Created! Please switch to Login.")
                except sqlite3.IntegrityError:
                    st.sidebar.error("This email is already registered.")
            else:
                st.sidebar.error("Use a valid email & password (min 4 chars).")
else:
    st.sidebar.info(f"Logged in as: {st.session_state.user_email}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()

# --- 5. MAIN PAGE CONTENT ---
if st.session_state.logged_in:
    st.title(f"💰 My Expense Log")
    
    # Currency Selector (Top right)
    currencies = ["$", "₹", "£", "€", "¥", "₱", "RM", "AED", "SAR"]
    new_curr = st.selectbox("Select Your Currency:", currencies, index=currencies.index(st.session_state.currency))
    
    # Save currency preference if changed
    if new_curr != st.session_state.currency:
        c.execute('UPDATE userstable SET currency = ? WHERE email = ?', (new_curr, st.session_state.user_email))
        conn.commit()
        st.session_state.currency = new_curr
        st.rerun()

    # Fast Entry Form
    st.write("### Add New Entry")
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            item_name = st.text_input("Item Name (e.g. Lunch)")
        with col2:
            item_cost = st.number_input("Cost", min_value=0.0, step=0.01)
        
        if st.form_submit_button("Save Item (Enter)", use_container_width=True):
            if item_name and item_cost > 0:
                today = datetime.now().strftime("%Y-%m-%d")
                c.execute('INSERT INTO expensestable(email, item, cost, date) VALUES (?,?,?,?)', 
                          (st.session_state.user_email, item_name, item_cost, today))
                conn.commit()
                st.toast(f"✅ Saved {item_name}")
                st.rerun()

    # Display Spending History
    st.write("---")
    c.execute('SELECT rowid, item, cost, date FROM expensestable WHERE email =? ORDER BY rowid DESC', (st.session_state.user_email,))
    history = c.fetchall()

    if history:
        df = pd.DataFrame(history, columns=["ID", "Item", "Cost", "Date"])
        
        # Summary
        total = df['Cost'].sum()
        st.metric("Total Spent", f"{st.session_state.currency} {total:,.2f}")
        
        # Table
        st.write("### Your Recent Items")
        st.dataframe(df[["Item", "Cost", "Date"]], use_container_width=True)

        # Simple Chart
        st.write("### Spending Breakdown")
        st.bar_chart(df, x="Item", y="Cost")

        # Delete Option
        with st.expander("🗑️ Delete a Mistake"):
            delete_item = st.selectbox("Select item to remove:", df['Item'].unique())
            if st.button("Delete Selected"):
                c.execute('DELETE FROM expensestable WHERE email=? AND item=?', (st.session_state.user_email, delete_item))
                conn.commit()
                st.success(f"Removed {delete_item}")
                st.rerun()
    else:
        st.info("Your list is empty. Start adding items above!")

else:
    # PUBLIC HOME PAGE
    st.title("💰 Global Expense Hero")
    st.subheader("The fastest way to track your daily spending.")
    
    st.markdown("""
    Welcome to a simple, private way to manage your money. 
    * **Personal Accounts:** Every user's data is private.
    * **Any Currency:** Works with USD, INR, EUR, and more.
    * **No Ads:** A clean, fast experience.
    
    **Please Login or Register using the sidebar to begin.**
    """)
    
    

st.write("---")
st.caption("© 2024 Expense Hero | Privacy-First Finance")
