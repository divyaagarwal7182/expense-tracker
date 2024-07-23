import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from hashlib import sha256

# Database connection setup
conn = sqlite3.connect('expenses.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                category TEXT,
                date TEXT,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id))''')
conn.commit()

# Helper functions for user authentication
def hash_password(password):
    return sha256(password.encode()).hexdigest()

def check_user(username, password):
    c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, hash_password(password)))
    return c.fetchone()

def create_user(username, password):
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def main_app():
    # Expense input form
    st.subheader('Add Expense')
    amount = st.number_input('Amount', min_value=0.0, format="%.2f")
    category = st.selectbox('Category', ['Food', 'Travel', 'Utilities', 'Entertainment', 'Other'])
    date = st.date_input('Date')
    description = st.text_area('Description')
    if st.button('Add Expense'):
        c.execute('INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
                  (st.session_state.user_id, amount, category, date, description))
        conn.commit()
        st.success('Expense added successfully!')

    # View and filter expenses
    st.subheader('View Expenses')
    df = pd.read_sql_query(f'SELECT * FROM expenses WHERE user_id={st.session_state.user_id}', conn)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        category_filter = st.multiselect('Filter by category', df['category'].unique())
        date_filter = st.date_input('Filter by date range', [])
        
        # Convert date_filter to datetime64[ns]
        if date_filter:
            date_filter = pd.to_datetime(date_filter)
        
        if category_filter:
            df = df[df['category'].isin(category_filter)]
        if len(date_filter) == 2:
            df = df[(df['date'] >= date_filter[0]) & (df['date'] <= date_filter[1])]

        # Display the table
        st.dataframe(df)

        # Delete expense
        st.subheader('Delete Expense')
        delete_expense_id = st.selectbox('Select Expense ID to Delete', df['id'])
        if st.button('Delete Selected Expense'):
            c.execute('DELETE FROM expenses WHERE id=?', (delete_expense_id,))
            conn.commit()
            st.success(f'Expense ID {delete_expense_id} deleted successfully!')
            st.experimental_rerun()  # Rerun to refresh the table

        # Analytics dashboard
        st.subheader('Analytics')
        if not df.empty:
            # Resample for monthly trend
            df.set_index('date', inplace=True)
            monthly_trend = df.resample('M').sum().reset_index()
            st.subheader('Monthly Expense Trend')
            st.line_chart(monthly_trend.set_index('date')['amount'])

            # Group by category for distribution
            category_distribution = df.groupby('category')['amount'].sum().reset_index()
            st.subheader('Expense Distribution by Category')
            st.bar_chart(category_distribution.set_index('category'))

            # Display summary table
            st.subheader('Expense Summary by Category')
            st.dataframe(category_distribution.sort_values(by='amount', ascending=False))

        # Export data
        st.subheader('Export Data')
        if st.button('Export to CSV'):
            df.to_csv('expenses.csv', index=False)
            st.success('Data exported to expenses.csv')
    else:
        st.write('No expenses to display.')

# Streamlit app
st.title('Personal Expense Tracker')

# Authentication
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.subheader('Login')
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        user = check_user(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.user_id = user[0]
            st.success('Logged in successfully!')
            st.experimental_rerun()  # Rerun the script after successful login

    st.subheader('Sign Up')
    new_username = st.text_input('New Username')
    new_password = st.text_input('New Password', type='password')
    if st.button('Sign Up'):
        if create_user(new_username, new_password):
            st.success('User created successfully! You can now log in.')
        else:
            st.error('Username already exists. Please choose a different username.')
else:
    st.sidebar.button('Logout', on_click=lambda: st.session_state.update(logged_in=False))
    main_app()

# Close the connection when done
conn.close()

