

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import date, timedelta, datetime
import calendar
import os



app = Flask(__name__)



app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "sqlite:///gym.db"
)

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


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


def get_plan_amount(plan):

    if "₹600" in plan:
        return 600

    elif "₹800" in plan:
        return 800
    elif "₹1500" in plan:
        return 1500

    elif "₹1800" in plan:
        return 1800

    elif "₹3800" in plan:
        return 3800

    return 0
def add_months(start_date, months):

    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1

    day = min(
        start_date.day,
        calendar.monthrange(year, month)[1]
    )

    return date(year, month, day)
@app.route("/register-member", methods=["POST"])
def register_member():

    plan = request.form["plan"]

    join_date = date.fromisoformat(
        request.form["join_date"]
    )

    if "3 Month" in plan or "VIP" in plan:
        expiry = add_months(join_date, 3)
    else:
        expiry = add_months(join_date, 1)

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
        join_date=join_date,
        expiry_date=expiry,
        cash_paid=0,
        online_paid=0,
        paid_amount=0,
        remaining_amount=plan_amount,
        payment_status="Pending",
        is_active=True
    )

    db.session.add(member)
    db.session.commit()

    return render_template("success.html")
    

@app.route("/owner-login", methods=["GET", "POST"])
def owner_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "owner" and password == "admin123":
            return redirect(url_for("owner_dashboard"))

        return "Invalid Username or Password"

    return render_template("owner-login.html")

class Payment(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    member_id = db.Column(
        db.Integer,
        db.ForeignKey("member.id")
    )

    amount = db.Column(db.Integer)

    payment_type = db.Column(db.String(20))

    payment_date = db.Column(
        db.Date,
        default=date.today
    )

    member = db.relationship("Member")
@app.route("/owner-dashboard")
def owner_dashboard():

    members = Member.query.all()

    total_members = Member.query.count()

    pending_fees = sum(
        member.remaining_amount
        for member in members
    )

    expiring_members = Member.query.filter(
        Member.expiry_date.isnot(None),
        Member.expiry_date <= date.today() + timedelta(days=3)
    ).all()

    expiry_alerts = len(expiring_members)

    today_attendance_count = Attendance.query.filter_by(
        date=date.today()
    ).count()

    weekly_collection = sum(
        payment.amount
        for payment in Payment.query.filter(
            Payment.payment_date >= date.today() - timedelta(days=7)
        ).all()
    )

    selected_month = request.args.get("month", type=int)

    if selected_month:
        monthly_collection = sum(
            payment.amount
            for payment in Payment.query.filter(
                db.extract("month", Payment.payment_date) == selected_month,
                db.extract("year", Payment.payment_date) == date.today().year
            ).all()
        )
    else:
        monthly_collection = 0

    yearly_collection = sum(
        payment.amount
        for payment in Payment.query.filter(
            Payment.payment_date >= date.today() - timedelta(days=365)
        ).all()
    )

    total_fees = sum(
        payment.amount
        for payment in Payment.query.all()
    )

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    filtered_collection = None

    if start_date and end_date:

        s = date.fromisoformat(start_date)
        e = date.fromisoformat(end_date)

        filtered_collection = sum(
            payment.amount
            for payment in Payment.query.filter(
                Payment.payment_date >= s,
                Payment.payment_date <= e
            ).all()
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
        current_date=date.today(),
        selected_month=selected_month,
        start_date=start_date,
        end_date=end_date,
        filtered_collection=filtered_collection
    )

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"))
    date = db.Column(db.Date, default=date.today)
    time = db.Column(db.Time,

    default=lambda:
(
    datetime.utcnow()
    + timedelta(hours=5, minutes=30)
).time()

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

        db.session.add(

         Payment(

            member_id=member.id,

            amount=remaining,

            payment_type="Cash"

        )

    )

    member.cash_paid += remaining

    member.paid_amount = member.cash_paid + member.online_paid
    member.remaining_amount = 0
    member.payment_status = "Paid"

    if "3 Month" in member.plan or "VIP" in    member.plan:
     member.expiry_date = add_months(date.today(), 3)
    else:
     member.expiry_date = add_months(date.today(), 1)

    db.session.commit()

    return redirect(url_for("owner_dashboard"))

@app.route("/partial-payment/<int:id>", methods=["POST"])
def partial_payment(id):

    member = Member.query.get_or_404(id)

    cash_now = int(request.form.get("cash_amount") or 0)
    online_now = int(request.form.get("online_amount") or 0)

    plan_amount = get_plan_amount(member.plan)

    new_total = (
        member.cash_paid
        + member.online_paid
        + cash_now
        + online_now
    )

    if new_total > plan_amount:
        return (
            f"Payment exceeds plan amount! "
            f"Maximum allowed is ₹{plan_amount}"
        )

    if cash_now > 0:
        db.session.add(
            Payment(
                member_id=member.id,
                amount=cash_now,
                payment_type="Cash"
            )
        )

    if online_now > 0:
        db.session.add(
            Payment(
                member_id=member.id,
                amount=online_now,
                payment_type="Online"
            )
        )

    member.cash_paid += cash_now
    member.online_paid += online_now

    member.paid_amount = member.cash_paid + member.online_paid
    member.remaining_amount = plan_amount - member.paid_amount

    if member.remaining_amount <= 0:
        member.remaining_amount = 0
        member.payment_status = "Paid"

    elif member.paid_amount > 0:
        member.payment_status = "Partial"

    else:
        member.payment_status = "Pending"

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
@app.route("/update-db")
def update_db():

    with db.engine.connect() as connection:

        connection.execute(
            db.text(
                """
                CREATE TABLE IF NOT EXISTS payment (
                    id SERIAL PRIMARY KEY,
                    member_id INTEGER,
                    amount INTEGER,
                    payment_type VARCHAR(20),
                    payment_date DATE DEFAULT CURRENT_DATE
                )
                """
            )
        )

        connection.commit()

    return "Payment table created successfully"
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
        member.expiry_date = add_months(date.today(), 3)
    else:
        member.expiry_date = add_months(date.today(), 1)

    db.session.commit()

    return redirect(url_for("owner_dashboard"))
@app.route("/init-db")
def init_db():

    db.create_all()

    return "Database tables created successfully!"

@app.route("/edit-member/<int:id>", methods=["GET", "POST"])
def edit_member(id):

    member = Member.query.get_or_404(id)

    if request.method == "POST":

        was_expired = (
            member.expiry_date is not None
            and member.expiry_date <= date.today()
        )

        member.plan = request.form["plan"]
        member.join_date = date.fromisoformat(request.form["join_date"])
        member.expiry_date = date.fromisoformat(request.form["expiry_date"])

        plan_amount = get_plan_amount(member.plan)

        if was_expired:
            member.cash_paid = 0
            member.online_paid = 0
            member.paid_amount = 0
            member.remaining_amount = plan_amount
            member.payment_status = "Pending"
            member.is_active = True
        else:
            member.remaining_amount = max(
                0,
                plan_amount - member.paid_amount
            )

            if member.remaining_amount <= 0:
                member.remaining_amount = 0
                member.payment_status = "Paid"

            elif member.paid_amount > 0:
                member.payment_status = "Partial"

            else:
                member.payment_status = "Pending"

        db.session.commit()

        return redirect(url_for("owner_dashboard"))

    return render_template(
    "edit-member.html",
    member=member,
    renew=request.args.get("renew"),
    current_date=date.today()
)
@app.route("/backup")
def backup():

    members = Member.query.all()

    output = "Gym No,Name,Phone,Age,Plan,Goal,Join Date,Expiry Date,Cash,Online,Total Paid,Remaining,Status\n"

    for m in members:
        output += f"{m.gym_number},{m.name},{m.phone},{m.age},{m.plan},{m.goal},{m.join_date},{m.expiry_date},{m.cash_paid},{m.online_paid},{m.paid_amount},{m.remaining_amount},{m.payment_status}\n"

    return output, 200, {
        "Content-Type": "text/csv",
        "Content-Disposition": "attachment; filename=gym_backup.csv"
    }
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

                if member.expiry_date and member.expiry_date < date.today():
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