from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "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"


DB_NAME = "pos.db"


# ----------------------------
# DATABASE
# ----------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT UNIQUE,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            company TEXT NOT NULL,
            net_weight TEXT,
            buy_price REAL NOT NULL,
            sell_price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def generate_product_code():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM products ORDER BY id DESC LIMIT 1")
    last = cursor.fetchone()
    conn.close()

    next_id = 1 if last is None else last["id"] + 1
    return str(next_id).zfill(8)   # 00000001


# ----------------------------
# ROUTES
# ----------------------------
@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    conn = get_db_connection()
    total_products = conn.execute("SELECT COUNT(*) AS count FROM products").fetchone()["count"]
    total_stock = conn.execute("SELECT COALESCE(SUM(stock), 0) AS total FROM products").fetchone()["total"]
    conn.close()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_stock=total_stock
    )


@app.route("/products")
def products():
    search = request.args.get("search", "").strip()

    conn = get_db_connection()
    if search:
        items = conn.execute("""
            SELECT * FROM products
            WHERE name LIKE ? OR category LIKE ? OR company LIKE ? OR product_code LIKE ?
            ORDER BY id DESC
        """, (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    else:
        items = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()

    return render_template("products.html", products=items, search=search)


@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        company = request.form.get("company", "").strip()
        net_weight = request.form.get("net_weight", "").strip()
        buy_price = request.form.get("buy_price", "").strip()
        sell_price = request.form.get("sell_price", "").strip()
        stock = request.form.get("stock", "").strip()

        if not name or not category or not company or not buy_price or not sell_price or not stock:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("add_product"))

        try:
            buy_price = float(buy_price)
            sell_price = float(sell_price)
            stock = int(stock)
        except ValueError:
            flash("Buy price, sell price, and stock must be valid numbers.", "danger")
            return redirect(url_for("add_product"))

        product_code = generate_product_code()

        try:
            conn = get_db_connection()
            conn.execute("""
                INSERT INTO products
                (product_code, name, category, company, net_weight, buy_price, sell_price, stock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (product_code, name, category, company, net_weight, buy_price, sell_price, stock))
            conn.commit()
            conn.close()

            flash("Product added successfully.", "success")
            return redirect(url_for("products"))

        except sqlite3.IntegrityError:
            flash("Product code already exists. Try again.", "danger")
            return redirect(url_for("add_product"))

    return render_template("add_product.html")


@app.route("/edit_product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    if product is None:
        conn.close()
        flash("Product not found.", "danger")
        return redirect(url_for("products"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        company = request.form.get("company", "").strip()
        net_weight = request.form.get("net_weight", "").strip()
        buy_price = request.form.get("buy_price", "").strip()
        sell_price = request.form.get("sell_price", "").strip()
        stock = request.form.get("stock", "").strip()

        if not name or not category or not company or not buy_price or not sell_price or not stock:
            conn.close()
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("edit_product", product_id=product_id))

        try:
            buy_price = float(buy_price)
            sell_price = float(sell_price)
            stock = int(stock)
        except ValueError:
            conn.close()
            flash("Buy price, sell price, and stock must be valid numbers.", "danger")
            return redirect(url_for("edit_product", product_id=product_id))

        conn.execute("""
            UPDATE products
            SET name = ?, category = ?, company = ?, net_weight = ?, buy_price = ?, sell_price = ?, stock = ?
            WHERE id = ?
        """, (name, category, company, net_weight, buy_price, sell_price, stock, product_id))
        conn.commit()
        conn.close()

        flash("Product updated successfully.", "success")
        return redirect(url_for("products"))

    conn.close()
    return render_template("edit_product.html", product=product)


@app.route("/delete_product/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

    flash("Product deleted successfully.", "success")
    return redirect(url_for("products"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
