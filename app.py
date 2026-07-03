from enum import member

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import date, timedelta, datetime
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
    gym_number = db.Column(db.Integer, unique=True)
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
    cash_paid = db.Column(db.Integer, default=0)
    online_paid = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

@app.route("/")
def home():
    return render_template("index.html")
def get_next_gym_number():

    last_member = Member.query.order_by(
        Member.gym_number.desc()
    ).first()

    if last_member and last_member.gym_number:
        return last_member.gym_number + 1

    return 1
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
    gym_number = get_next_gym_number()
    member = Member(

    gym_number=gym_number,

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

    pending_fees = sum(
        member.remaining_amount
        for member in members
    )

    expiring_members = Member.query.filter(
        Member.expiry_date <= date.today() + timedelta(days=3)
    ).all()

    expiry_alerts = len(expiring_members)

    today_attendance_count = Attendance.query.filter_by(
     date=date.today()
    ).count()

    weekly_collection = sum(
        member.paid_amount
        for member in members
        if member.join_date >= date.today() - timedelta(days=7)
    )

    monthly_collection = sum(
        member.paid_amount
        for member in members
        if member.join_date >= date.today() - timedelta(days=30)
    )

    yearly_collection = sum(
        member.paid_amount
        for member in members
        if member.join_date >= date.today() - timedelta(days=365)
    )

    total_fees = sum(
        member.paid_amount
        for member in members
    )

    return render_template(
        "owner-dashboard.html",
        members=members,
        total_members=total_members,
        pending_fees=pending_fees,
        total_fees=total_fees,
        expiry_alerts=expiry_alerts,
        expiring_members=expiring_members,
        today_attendance_count=today_attendance_count,
        weekly_collection=weekly_collection,
        monthly_collection=monthly_collection,
        yearly_collection=yearly_collection,
        current_date=date.today()
    )
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"))
    date = db.Column(db.Date, default=date.today)
    time = db.Column(db.Time,

    default=lambda:

    datetime.now().time()

)
    member = db.relationship("Member")

    
@app.route("/delete-member/<int:id>")
def delete_member(id):

    member = Member.query.get_or_404(id)

    Attendance.query.filter_by(member_id=member.id).delete()

    db.session.delete(member)
    db.session.commit()

    return redirect(url_for("owner_dashboard"))
@app.route("/mark-paid/<int:id>")
def mark_paid(id):
    member = Member.query.get_or_404(id)

    plan_amount = get_plan_amount(member.plan)

    remaining = plan_amount - (member.cash_paid + member.online_paid)

    if remaining > 0:
        member.cash_paid += remaining

    member.paid_amount = member.cash_paid + member.online_paid
    member.remaining_amount = 0
    member.payment_status = "Paid"

    if "3 Month" in member.plan or "VIP" in member.plan:
        member.expiry_date = date.today() + timedelta(days=90)
    else:
        member.expiry_date = date.today() + timedelta(days=30)

    db.session.commit()

    return redirect(url_for("owner_dashboard"))
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
@app.route("/payment-success/<int:id>/<int:amount>")
def payment_success(id, amount):

    member = Member.query.get_or_404(id)

    plan_amount = get_plan_amount(member.plan)

    member.paid_amount += amount

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

    return redirect(
        url_for(
            "member_dashboard",
            id=member.id
        )
    )
@app.route("/partial-payment/<int:id>", methods=["POST"])
def partial_payment(id):
    member = Member.query.get_or_404(id)

    cash_now = int(request.form.get("cash_amount") or 0)
    online_now = int(request.form.get("online_amount") or 0)

    plan_amount = get_plan_amount(member.plan)

    member.cash_paid += cash_now
    member.online_paid += online_now

    member.paid_amount = member.cash_paid + member.online_paid
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
@app.route("/deactivate-member/<int:id>")
def deactivate_member(id):
    member = Member.query.get_or_404(id)

    member.is_active = False
    db.session.commit()

    return redirect(url_for("owner_dashboard"))


@app.route("/activate-member/<int:id>")
def activate_member(id):
    member = Member.query.get_or_404(id)

    member.is_active = True
    db.session.commit()

    return redirect(url_for("owner_dashboard"))
@app.route('/update-db')
def update_db():

    with db.engine.connect() as connection:

        try:
            connection.execute(
                db.text(
                    "ALTER TABLE attendance ADD COLUMN time TIME"
                )
            )

        except:
            pass

        db.session.commit()

    return "Database Updated Successfully"
@app.route("/renew-member/<int:id>")
def renew_member(id):

    member = Member.query.get_or_404(id)

    plan_amount = get_plan_amount(member.plan)

    member.cash_paid = 0
    member.online_paid = 0
    member.paid_amount = 0
    member.remaining_amount = plan_amount
    member.payment_status = "Pending"
    member.is_active = True

    if "3 Month" in member.plan or "VIP" in member.plan:
        member.expiry_date = date.today() + timedelta(days=90)
    else:
        member.expiry_date = date.today() + timedelta(days=30)

    db.session.commit()

    return redirect(url_for("owner_dashboard"))
@app.route("/init-db")
def init_db():
    db.create_all()
    return "Database tables created successfully!"
@app.route("/pay-partial/<int:id>", methods=["POST"])
def pay_partial(id):
    member = Member.query.get_or_404(id)

    amount = int(request.form["amount"])

    order = client.order.create({
        "amount": amount * 100,
        "currency": "INR",
        "payment_capture": 1
    })

    return render_template(
        "payment.html",
        member=member,
        order=order,
        amount=amount,
        partial=True
    )
@app.route("/edit-member/<int:id>", methods=["GET", "POST"])
def edit_member(id):

    member = Member.query.get_or_404(id)

    if request.method == "POST":

        member.plan = request.form["plan"]
        member.join_date = date.fromisoformat(request.form["join_date"])
        member.expiry_date = date.fromisoformat(request.form["expiry_date"])

        plan_amount = get_plan_amount(member.plan)

        member.remaining_amount = max(
        0,
        plan_amount - member.paid_amount)

        if member.remaining_amount <= 0:
            member.remaining_amount = 0
            member.payment_status = "Paid"

        elif member.paid_amount > 0:
            member.payment_status = "Partial"

        else:
            member.payment_status = "Pending"

        db.session.commit()

        return redirect(url_for("owner_dashboard"))

    return render_template("edit-member.html", member=member)
@app.route("/attendance", methods=["GET", "POST"])
def attendance():

    message = ""

    if request.method == "POST":

        gym_number = int(request.form["gym_number"])

        member = Member.query.filter_by(
            gym_number=gym_number
        ).first()

        if not member:
            message = "Member not found"

        elif not member.is_active:
            message = (
                f"⚠ {member.name} is Deactivated. "
                f"Attendance not marked."
            )

        else:
            today_attendance = Attendance.query.filter_by(
                member_id=member.id,
                date=date.today()
            ).first()

            if today_attendance:
                message = f"{member.name} already marked present today"

            else:
                attendance = Attendance(
                    member_id=member.id
                )

                db.session.add(attendance)
                db.session.commit()

                if member.expiry_date < date.today():
                    message = (
                        f"⚠ {member.name} attendance marked successfully "
                        f"but membership expired on {member.expiry_date}"
                    )

                elif member.remaining_amount > 0:
                    message = (
                        f"⚠ {member.name} attendance marked successfully "
                        f"but fees remaining ₹{member.remaining_amount}"
                    )

                else:
                    message = f"{member.name} attendance marked successfully"

    today_records = Attendance.query.filter_by(
        date=date.today()
    ).all()

    today_count = len(today_records)

    selected_date = request.args.get("selected_date")

    history_records = []

    if selected_date:
        filter_date = date.fromisoformat(selected_date)

        history_records = Attendance.query.filter(
            Attendance.date == filter_date
        ).order_by(
            Attendance.date.desc()
        ).all()

    return render_template(
        "attendance.html",
        message=message,
        today_records=today_records,
        history_records=history_records,
        today_count=today_count,
        selected_date=selected_date
    )
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)