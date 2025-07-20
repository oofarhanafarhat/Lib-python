# app.py
import streamlit as st
import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict

# ---------- DOMAIN LAYER ----------
class User(ABC):
    def __init__(self, user_id: str, name: str):  # ✅ fixed _init_ → __init__
        self._user_id = user_id
        self._name = name

    @property
    def user_id(self): return self._user_id
    @property
    def name(self): return self._name

class Member(User):
    MAX_BORROW = 5

    def __init__(self, user_id: str, name: str):  # ✅ fixed _init_
        super().__init__(user_id, name)
        self._loans: List["Loan"] = []

    def borrow(self, book: "Book") -> str:
        if len(self._loans) >= Member.MAX_BORROW:
            return f"❌ {self._name} already has {Member.MAX_BORROW} books."
        if book.available_copies <= 0:
            return f"❌ '{book.title}' is not available."
        loan = Loan(book, self)
        self._loans.append(loan)
        book.decrease_copy()
        return f"✅ '{book.title}' borrowed by {self._name}."

    def return_book(self, loan_index: int) -> str:
        try:
            loan = self._loans.pop(loan_index)
            loan.close()
            loan.book.increase_copy()
            return f"✅ '{loan.book.title}' returned by {self._name}."
        except IndexError:
            return "❌ Invalid loan index."

    def dashboard(self) -> Dict:
        today = dt.date.today()
        return {
            "name": self._name,
            "loans": [
                {
                    "title": l.book.title,
                    "type": l.book.type,
                    "due": l.due_date.isoformat(),
                    "overdue": l.due_date < today
                }
                for l in self._loans
            ]
        }

class Librarian(User):
    def __init__(self, user_id: str, name: str):  # ✅ fixed _init_
        super().__init__(user_id, name)

    def add_book(self, book: "Book"):
        st.session_state.inventory[book.isbn] = book

    def remove_book(self, isbn: str):
        st.session_state.inventory.pop(isbn, None)

    def dashboard(self) -> Dict:
        return {
            "inventory": [
                {
                    "isbn": b.isbn,
                    "title": b.title,
                    "type": b.type,
                    "copies": b.available_copies
                }
                for b in st.session_state.inventory.values()
            ]
        }

class Book(ABC):
    def __init__(self, isbn: str, title: str, total_copies: int):  # ✅ fixed _init_
        self.isbn = isbn
        self.title = title
        self._total = total_copies
        self._available = total_copies

    @property
    def available_copies(self): return self._available
    def decrease_copy(self): self._available -= 1
    def increase_copy(self): self._available += 1

    @property
    @abstractmethod
    def type(self): ...

class PhysicalBook(Book):
    def __init__(self, isbn: str, title: str, total_copies: int):  # ✅ added constructor
        super().__init__(isbn, title, total_copies)

    @property
    def type(self): return "Physical"

class Ebook(Book):
    def __init__(self, isbn: str, title: str, total_copies: int):  # ✅ added constructor
        super().__init__(isbn, title, total_copies)

    @property
    def type(self): return "Ebook"

@dataclass
class Loan:
    book: Book
    member: Member
    borrow_date: dt.date = field(default_factory=dt.date.today)
    due_date: dt.date = field(init=False)

    def __post_init__(self):  # ✅ fixed _post_init_
        days = 7 if isinstance(self.book, PhysicalBook) else 14
        self.due_date = self.borrow_date + dt.timedelta(days=days)

    def close(self):
        pass  # Placeholder for ebook return handling

class LoanManager:
    @staticmethod
    def auto_return_ebooks():
        today = dt.date.today()
        for member in st.session_state.members.values():
            still_open = []
            for loan in member._loans:
                if isinstance(loan.book, Ebook) and loan.due_date < today:
                    loan.book.increase_copy()
                else:
                    still_open.append(loan)
            member._loans = still_open

# ---------- STREAMLIT UI ----------
st.set_page_config(page_title="Library & eBook System", layout="wide")

# ---------- SESSION STATE ----------
if "inventory" not in st.session_state:
    st.session_state.inventory = {}  # ✅ fixed indentation

    # ✅ seed demo data inside this block
    st.session_state.inventory["111"] = PhysicalBook("111", "Python 101", 3)
    st.session_state.inventory["222"] = Ebook("222", "Streamlit in Action", 5)

if "members" not in st.session_state:
    st.session_state.members = {}  # ✅ removed type hinting here
    st.session_state.members["alice"] = Member("alice", "Alice")
    st.session_state.members["bob"] = Member("bob", "Bob")

if "librarians" not in st.session_state:
    st.session_state.librarians = {}
    st.session_state.librarians["lib1"] = Librarian("lib1", "Mr. Giles")

# ---------- AUTO-RETURN FOR EBOOKS ----------
LoanManager.auto_return_ebooks()

# ---------- NAVIGATION ----------
role = st.sidebar.selectbox("Login as", ["Member", "Librarian"])

if role == "Member":
    member: Member = st.sidebar.selectbox(
        "Select Member",
        options=list(st.session_state.members.values()),
        format_func=lambda m: m.name
    )
    st.title(f"📚 Member Dashboard – {member.name}")
    dash = member.dashboard()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📖 Available Books")
        for book in st.session_state.inventory.values():
            if book.available_copies > 0:
                if st.button(f"Borrow '{book.title}' ({book.type})"):
                    msg = member.borrow(book)
                    st.success(msg)
                    st.rerun()

    with col2:
        st.subheader("📑 My Loans")
        if dash["loans"]:
            for idx, loan in enumerate(dash["loans"]):
                st.write(f"{idx + 1}. {loan['title']} ({loan['type']}) – due {loan['due']}")
                if loan["overdue"]:
                    st.error("OVERDUE!")
                if loan["type"] == "Physical":
                    if st.button(f"Return {loan['title']}", key=f"ret{idx}"):
                        msg = member.return_book(idx)
                        st.success(msg)
                        st.rerun()
        else:
            st.info("No active loans.")

else:
    librarian: Librarian = st.sidebar.selectbox(
        "Select Librarian",
        options=list(st.session_state.librarians.values()),
        format_func=lambda l: l.name
    )
    st.title(f"🧑‍🏫 Librarian Dashboard – {librarian.name}")
    dash = librarian.dashboard()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📚 Inventory")
        st.dataframe(dash["inventory"])

        st.subheader("➕ Add Book")
        with st.form("add_book"):
            isbn = st.text_input("ISBN")
            title = st.text_input("Title")
            copies = st.number_input("Total Copies", min_value=1, value=1)
            book_type = st.selectbox("Type", ["Physical", "Ebook"])
            submitted = st.form_submit_button("Add")
            if submitted and isbn and title:
                book = PhysicalBook(isbn, title, copies) if book_type == "Physical" else Ebook(isbn, title, copies)
                librarian.add_book(book)
                st.success("Book added.")
                st.rerun()

    with col2:
        st.subheader("➖ Remove Book")
        to_remove = st.selectbox("Select ISBN to remove", list(st.session_state.inventory.keys()))
        if st.button("Remove"):
            librarian.remove_book(to_remove)
            st.success("Book removed.")
            st.rerun()
