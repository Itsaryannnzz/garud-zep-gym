from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import date, timedelta
from flask import send_file
from reportlab.pdfgen import canvas
import io
import razorpay
import os

app = Flask(__name__)



app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "sqlite:///gym.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
client = razorpay.Client(
    auth=(
        "rzp_test_T7Uqz37x8YboyU",
        "9P1mS7NkpFpe1JHAmOfr5h09"
    )
)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    age = db.Column(db.Integer)
    plan = db.Column(db.String(100))
    goal = db.Column(db.String(100))
    join_date = db.Column(db.Date, default=date.today)
    expiry_date = db.Column(db.Date)
    payment_status = db.Column(db.String(20), default="Pending")
    paid_amount = db.Column(db.Integer, default=0)
    remaining_amount = db.Column(db.Integer, default=0)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register-member", methods=["POST"])
def register_member():

    plan = request.form["plan"]

    if "3 Month" in plan or "VIP" in plan:
        expiry = date.today() + timedelta(days=90)
    else:
        expiry = date.today() + timedelta(days=30)

    existing_member = Member.query.filter(
    (Member.name == request.form["name"]) |
    (Member.phone == request.form["phone"])
).first()

    if existing_member:
        return "Member already exists!"
    plan_amount = get_plan_amount(plan)
    member = Member(
    name=request.form["name"],
    phone=request.form["phone"],
    age=int(request.form["age"]),
    plan=plan,
    goal=request.form["goal"],
    expiry_date=expiry,

    paid_amount=0,
    remaining_amount=plan_amount
)

    db.session.add(member)
    db.session.commit()

    return render_template("success.html")
def get_plan_amount(plan):
    if "₹600" in plan:
        return 600
    elif "₹800" in plan:
        return 800
    elif "₹1800" in plan:
        return 1800
    elif "₹3999" in plan:
        return 3999
    return 0

@app.route("/owner-login", methods=["GET", "POST"])
def owner_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "owner" and password == "admin123":
            return redirect(url_for("owner_dashboard"))

        return "Invalid Username or Password"

    return render_template("owner-login.html")

@app.route("/owner-dashboard")
def owner_dashboard():
    members = Member.query.all()
    total_members = Member.query.count()
    pending_fees = Member.query.filter_by(payment_status="Pending").count()

    expiry_alerts = Member.query.filter(
        Member.expiry_date <= date.today() + timedelta(days=1)
    ).count()

    total_fees = 0

    for member in members:
        if member.payment_status == "Paid":
            if "₹600" in member.plan:
                total_fees += 600
            elif "₹800" in member.plan:
                total_fees += 800
            elif "₹1800" in member.plan:
                total_fees += 1800
            elif "₹3999" in member.plan:
                total_fees += 3999

    return render_template(
        "owner-dashboard.html",
        members=members,
        total_members=total_members,
        pending_fees=pending_fees,
        total_fees=total_fees,
        expiry_alerts=expiry_alerts
    )

    
@app.route("/delete-member/<int:id>")
def delete_member(id):

    member = Member.query.get_or_404(id)

    db.session.delete(member)

    db.session.commit()

    return redirect(url_for("owner_dashboard"))
@app.route("/mark-paid/<int:id>")
def mark_paid(id):
    member = Member.query.get_or_404(id)

    member.payment_status = "Paid"

    if "3 Month" in member.plan or "VIP" in member.plan:
        member.expiry_date = date.today() + timedelta(days=90)
    else:
        member.expiry_date = date.today() + timedelta(days=30)

    db.session.commit()

    return redirect(url_for("owner_dashboard"))
@app.route("/receipt/<int:id>")
def receipt(id):

    member = Member.query.get_or_404(id)

    return render_template(
        "receipt.html",
        member=member
    )
@app.route("/download-receipt/<int:id>")
def download_receipt(id):
    member = Member.query.get_or_404(id)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(180, 800, "GARUD ZEP GYM")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 740, f"Receipt ID: GZG-{member.id}")
    pdf.drawString(100, 710, f"Name: {member.name}")
    pdf.drawString(100, 680, f"Phone: {member.phone}")
    pdf.drawString(100, 650, f"Plan: {member.plan}")
    pdf.drawString(100, 620, f"Status: {member.payment_status}")
    pdf.drawString(100, 590, f"Join Date: {member.join_date}")
    pdf.drawString(100, 560, f"Expiry Date: {member.expiry_date}")

    pdf.drawString(100, 500, "Thank you for joining Garud Zep Gym.")

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"receipt_{member.name}.pdf",
        mimetype="application/pdf"
    )
@app.route("/member-login", methods=["GET", "POST"])
def member_login():
    if request.method == "POST":
        phone = request.form["phone"]

        member = Member.query.filter_by(phone=phone).first()

        if member:
            return redirect(url_for("member_dashboard", id=member.id))

        return "Member Not Found"

    return render_template("member-login.html")


@app.route("/member-dashboard/<int:id>")
def member_dashboard(id):
    member = Member.query.get_or_404(id)

    return render_template("member-dashboard.html", member=member)
@app.route("/pay/<int:id>")
def pay(id):

    member = Member.query.get_or_404(id)

    amount = 0

    if "₹600" in member.plan:
        amount = 600

    elif "₹800" in member.plan:
        amount = 800

    elif "₹1800" in member.plan:
        amount = 1800

    elif "₹3999" in member.plan:
        amount = 3999

    order = client.order.create({

        "amount": amount * 100,

        "currency": "INR",

        "payment_capture": 1

    })

    return render_template(

        "payment.html",

        member=member,

        order=order,

        amount=amount

    )
@app.route("/payment-success/<int:id>")
def payment_success(id):
    member = Member.query.get_or_404(id)

    member.payment_status = "Paid"

    if "3 Month" in member.plan or "VIP" in member.plan:
        member.expiry_date = date.today() + timedelta(days=90)
    else:
        member.expiry_date = date.today() + timedelta(days=30)

    db.session.commit()

    return redirect(url_for("member_dashboard", id=member.id))
@app.route("/partial-payment/<int:id>", methods=["POST"])
def partial_payment(id):
    member = Member.query.get_or_404(id)

    paid_now = int(request.form["paid_amount"])
    plan_amount = get_plan_amount(member.plan)

    member.paid_amount += paid_now
    member.remaining_amount = plan_amount - member.paid_amount

    if member.remaining_amount <= 0:
        member.remaining_amount = 0
        member.payment_status = "Paid"

        if "3 Month" in member.plan or "VIP" in member.plan:
            member.expiry_date = date.today() + timedelta(days=90)
        else:
            member.expiry_date = date.today() + timedelta(days=30)
    else:
        member.payment_status = "Partial"

    db.session.commit()

    return redirect(url_for("owner_dashboard"))

@app.route("/update-db")
def update_db():
    with db.engine.connect() as connection:
        connection.execute(db.text("ALTER TABLE member ADD COLUMN IF NOT EXISTS paid_amount INTEGER DEFAULT 0"))
        connection.execute(db.text("ALTER TABLE member ADD COLUMN IF NOT EXISTS remaining_amount INTEGER DEFAULT 0"))
        connection.commit()

    return "Database updated successfully!"
@app.route("/init-db")
def init_db():
    db.create_all()
    return "Database tables created successfully!"

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)