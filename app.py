from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nexora_pos_secret_key"


DB_NAME = "pos.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT UNIQUE,
            product_name TEXT NOT NULL,
            category TEXT,
            company TEXT,
            net_weight TEXT,
            retail_price REAL NOT NULL DEFAULT 0,
            wholesale_price REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE,
            customer_name TEXT,
            payment_type TEXT,
            total_amount REAL NOT NULL DEFAULT 0,
            sale_date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            qty INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)

    conn.commit()
    conn.close()


def generate_product_code():
    conn = get_db_connection()
    row = conn.execute("SELECT id FROM products ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()

    next_id = 1
    if row:
        next_id = row["id"] + 1
    return str(next_id).zfill(8)


def generate_invoice_no():
    return "INV" + datetime.now().strftime("%Y%m%d%H%M%S")


init_db()


@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    conn = get_db_connection()

    total_products = conn.execute("SELECT COUNT(*) AS count FROM products").fetchone()["count"]
    total_stock = conn.execute("SELECT COALESCE(SUM(stock), 0) AS total FROM products").fetchone()["total"]
    total_sales = conn.execute("SELECT COUNT(*) AS count FROM sales").fetchone()["count"]
    revenue = conn.execute("SELECT COALESCE(SUM(total_amount), 0) AS total FROM sales").fetchone()["total"]

    recent_sales = conn.execute("""
        SELECT * FROM sales
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_stock=total_stock,
        total_sales=total_sales,
        revenue=revenue,
        recent_sales=recent_sales
    )


@app.route("/products")
def products():
    search = request.args.get("search", "").strip()

    conn = get_db_connection()
    if search:
        product_list = conn.execute("""
            SELECT * FROM products
            WHERE product_name LIKE ? OR category LIKE ? OR company LIKE ? OR product_code LIKE ?
            ORDER BY id DESC
        """, (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    else:
        product_list = conn.execute("""
            SELECT * FROM products
            ORDER BY id DESC
        """).fetchall()

    conn.close()
    return render_template("products.html", products=product_list, search=search)


@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        product_code = generate_product_code()
        product_name = request.form.get("product_name", "").strip()
        category = request.form.get("category", "").strip()
        company = request.form.get("company", "").strip()
        net_weight = request.form.get("net_weight", "").strip()

        try:
            retail_price = float(request.form.get("retail_price", 0) or 0)
            wholesale_price = float(request.form.get("wholesale_price", 0) or 0)
            stock = int(request.form.get("stock", 0) or 0)
        except ValueError:
            flash("Invalid price or stock value.", "danger")
            return redirect(url_for("add_product"))

        if not product_name:
            flash("Product name is required.", "danger")
            return redirect(url_for("add_product"))

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO products (
                product_code, product_name, category, company, net_weight,
                retail_price, wholesale_price, stock, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_code, product_name, category, company, net_weight,
            retail_price, wholesale_price, stock, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()

        flash("Product added successfully.", "success")
        return redirect(url_for("products"))

    return render_template("add_product.html")


@app.route("/edit_product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    if not product:
        conn.close()
        flash("Product not found.", "danger")
        return redirect(url_for("products"))

    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        category = request.form.get("category", "").strip()
        company = request.form.get("company", "").strip()
        net_weight = request.form.get("net_weight", "").strip()

        try:
            retail_price = float(request.form.get("retail_price", 0) or 0)
            wholesale_price = float(request.form.get("wholesale_price", 0) or 0)
            stock = int(request.form.get("stock", 0) or 0)
        except ValueError:
            conn.close()
            flash("Invalid price or stock value.", "danger")
            return redirect(url_for("edit_product", product_id=product_id))

        conn.execute("""
            UPDATE products
            SET product_name = ?, category = ?, company = ?, net_weight = ?,
                retail_price = ?, wholesale_price = ?, stock = ?
            WHERE id = ?
        """, (
            product_name, category, company, net_weight,
            retail_price, wholesale_price, stock, product_id
        ))
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


@app.route("/sales", methods=["GET", "POST"])
def sales():
    conn = get_db_connection()

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        payment_type = request.form.get("payment_type", "cash").strip()

        product_ids = request.form.getlist("product_id[]")
        qtys = request.form.getlist("qty[]")

        if not product_ids or not qtys or len(product_ids) != len(qtys):
            conn.close()
            flash("Invalid sale items.", "danger")
            return redirect(url_for("sales"))

        cart_items = []
        total_amount = 0

        for i in range(len(product_ids)):
            try:
                product_id = int(product_ids[i])
                qty = int(qtys[i])
            except ValueError:
                conn.close()
                flash("Invalid product or quantity.", "danger")
                return redirect(url_for("sales"))

            if qty <= 0:
                conn.close()
                flash("Quantity must be greater than 0.", "danger")
                return redirect(url_for("sales"))

            product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

            if not product:
                conn.close()
                flash("Product not found.", "danger")
                return redirect(url_for("sales"))

            if product["stock"] < qty:
                conn.close()
                flash(f"Not enough stock for {product['product_name']}.", "danger")
                return redirect(url_for("sales"))

            unit_price = product["retail_price"]
            subtotal = unit_price * qty
            total_amount += subtotal

            cart_items.append({
                "product_id": product["id"],
                "product_name": product["product_name"],
                "qty": qty,
                "unit_price": unit_price,
                "subtotal": subtotal
            })

        invoice_no = generate_invoice_no()

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sales (invoice_no, customer_name, payment_type, total_amount, sale_date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            invoice_no,
            customer_name,
            payment_type,
            total_amount,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        sale_id = cur.lastrowid

        for item in cart_items:
            cur.execute("""
                INSERT INTO sale_items (sale_id, product_id, product_name, qty, unit_price, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                sale_id,
                item["product_id"],
                item["product_name"],
                item["qty"],
                item["unit_price"],
                item["subtotal"]
            ))

            cur.execute("""
                UPDATE products
                SET stock = stock - ?
                WHERE id = ?
            """, (item["qty"], item["product_id"]))

        conn.commit()
        conn.close()

        flash(f"Sale completed successfully. Invoice: {invoice_no}", "success")
        return redirect(url_for("view_sale", sale_id=sale_id))

    product_list = conn.execute("""
        SELECT * FROM products
        WHERE stock > 0
        ORDER BY product_name ASC
    """).fetchall()

    conn.close()
    return render_template("sales.html", products=product_list)


@app.route("/sale/<int:sale_id>")
def view_sale(sale_id):
    conn = get_db_connection()

    sale = conn.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
    items = conn.execute("""
        SELECT * FROM sale_items
        WHERE sale_id = ?
    """, (sale_id,)).fetchall()

    conn.close()

    if not sale:
        flash("Sale not found.", "danger")
        return redirect(url_for("dashboard"))

    return render_template("view_sale.html", sale=sale, items=items)


@app.route("/reports")
def reports():
    conn = get_db_connection()

    sales_list = conn.execute("""
        SELECT * FROM sales
        ORDER BY id DESC
    """).fetchall()

    product_list = conn.execute("""
        SELECT * FROM products
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template("reports.html", sales=sales_list, products=product_list)


@app.route("/stock_in/<int:product_id>", methods=["POST"])
def stock_in(product_id):
    try:
        qty = int(request.form.get("qty", 0))
    except ValueError:
        flash("Invalid stock quantity.", "danger")
        return redirect(url_for("products"))

    if qty <= 0:
        flash("Stock quantity must be greater than 0.", "danger")
        return redirect(url_for("products"))

    conn = get_db_connection()
    conn.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (qty, product_id))
    conn.commit()
    conn.close()

    flash("Stock updated successfully.", "success")
    return redirect(url_for("products"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
