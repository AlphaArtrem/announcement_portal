import sqlite3
import pandas
from flask import Flask, render_template, request, session ,redirect,jsonify
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
import time
import datetime

# Initializing flask app
app = Flask(__name__)

# User session
app.secret_key = "4#as6d#49fs&aas546sf$asba57e4e54#2$@2/w"

# Loading databases
accounts = sqlite3.connect("accounts.db",check_same_thread=False)
notice = sqlite3.connect("notices.db",check_same_thread=False)
messagesdb = sqlite3.connect("messages.db",check_same_thread=False)

# Database Cursors
accur = accounts.cursor()
notcur = notice.cursor()
mescur = messagesdb.cursor()

"""Account Section"""

#When Default Directory Is Accessed
@app.route("/")
def home():
    # getting latest announcments
    list = pandas.read_sql_query("SELECT * FROM notices ORDER BY id DESC",notice)
    # Converting DataFrame to List of Dicts
    list = list.to_dict("records")
    # Converting list to only few annoucement
    list = list[0:5]
    return render_template("index.html",login=session,notices=list)

# When register page is visted
@app.route("/register", methods = ["POST", "GET"])
def register():
    # when user is not logged in and reuest register page
    if not session and request.method == "GET":
        return render_template("register.html",login=session)
    # when user is logged in and requests register page again
    elif session:
        return redirect("/logged")
    elif request.method == "POST":
        # getting form input fields
        username = request.form.get("username")
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        type = request.form.get("type")
        password = request.form.get("password")
        confirm = request.form.get("confirmpassword")
        # if any field is empty
        if not username or not firstname or not lastname or not type or not password or not confirm:
            return render_template("register.html",login=session,alert="You must provide all the fields")
        # if confirmation and password doesn't match
        if password != confirm :
            return render_template("register.html",login=session,alert="Password And Confirmation Must Match")
        # checking if username exists
        info = pandas.read_sql_query("SELECT * FROM students where username =?",accounts ,params = (username,))
        # if the requested account doesn't exist
        if not info.empty:
            return render_template("register.html",login=session,alert="Username Alredy Taken")
        else:
            # generate password hash to store in database
            password = generate_password_hash(password)
            # for student type account activate account immediately
            if type == "student":
                accur.execute("INSERT INTO students(username,password,firstname,lastname,type,allowed) VALUES (?,?,?,?,?,?)",(username,password,firstname,lastname,type,1))
            # for teacher account type do not activate account until manually activated by admin
            else:
                accur.execute("INSERT INTO students(username,password,firstname,lastname,type,allowed) VALUES (?,?,?,?,?,?)",(username,password,firstname,lastname,type,0))
            accounts.commit()
            return redirect("/login")

# When Login page is visted
@app.route("/login", methods = ["GET", "POST"])
def login():
    # if user is not logged in and request login page
    if not session and request.method == "GET":
        return render_template("login.html",login=session)
    # if user is already logged in and requests login page again
    elif session:
        return redirect("/logged")
    else:
        # getting form fields
        username = request.form.get("username")
        type = request.form.get("type")
        password = request.form.get("password")
        # if any field is empty
        if not username or not password:
            return render_template("login.html",login=session,alert="You must provide all fields")
        else:
            # getting requested users account credentials
            info = pandas.read_sql_query("SELECT * FROM students where username =?",accounts ,params = (username,))
            # if the requested account doesn't exist
            if info.empty:
                return render_template("login.html",login=session,alert="No such account exists")
            # if the pasword doesn't match
            elif not check_password_hash(info["password"][0],password):
                return render_template("login.html",login=session,alert="Incorrect Username or Password")
            # if the account is active
            elif int(info["allowed"][0]) == 0:
                return render_template("login.html",login=session,alert="Account isn't active contact the admin")
            else:
                # storing user session values
                session["type"] = info["type"][0]
                session["name"] = info["firstname"][0]
                session["lastname"] = info["lastname"][0]
                session["username"] = info["username"][0]
                session["id"] = int(info["id"][0])
                return redirect("/announcements")

# For Changing User password
@app.route("/changepass",methods=["GET","POST"])
def changepass():
    # if loged in
    if session:
        # When page is accessed
        if request.method == "GET":
            return render_template("changepass.html",login=session)
        # When change request is made
        else:
            # Getting values from form
            old = request.form.get("old")
            new = request.form.get("new")
            confirm = request.form.get("confirm")
            # getting  users account credentials
            info = pandas.read_sql_query("SELECT * FROM students where id =?",accounts ,params = (session["id"],))
            # If any field is not provided
            if not old or not new or not confirm:
                return render_template("changepass.html",login=session,alert="All filed are requried")
            # If new password and confirmation doesn't match
            elif new != confirm:
                return render_template("changepass.html",login=session,alert="New Password And Confirmation Must Match")
            # if old password is incorrect
            elif not check_password_hash(info["password"][0],old):
                return render_template("changepass.html",login=session,alert="Incorrect Old Password")
            # get new password hash
            password = generate_password_hash(new)
            # udating password
            accur.execute("UPDATE students SET password = ? WHERE id = ?;",(password,session["id"]))
            # commit return none on successfull execution
            # and true when when combined with not and sucessfull execution occurs
            if not accounts.commit():
                return render_template("changepass.html",login=session,done="success")
            else:
                return render_template("changepass.html",login=session,done="fail")
    # if not logged in
    else:
        return redirect("/denied")

# When profile page is visted
@app.route("/profile")
def profile():
    if session:
        return render_template("profile.html",login=session)
    else:
         return redirect("/denied")

# When logout page is visted
@app.route("/logout")
def logout():
    # Clear user's session
    session.clear()
    # Redirect to homepage
    return redirect("/")

"""Announcement Section"""

# for adding announcement
@app.route("/add",methods=["GET","POST"])
def add():
    # if logged in as teacher
    if session["type"] == "teacher":
        # Getting no of seconds from epoch
        timestamp = time.time()
        # converting seconds to readable date time format
        timestamp = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        # if reuested html page
        if request.method == "GET":
            return render_template("add.html",login=session)
        # when sent via post
        else:
            # getting announcement
            announcement = request.form.get("announcement")
            # if annoucement not provided
            if not announcement:
                return redirect("/add")
            # if provided
            else:
                # executing sql entry
                notcur.execute("INSERT INTO notices (announcement,timestamp,userid,name) VALUES (?,?,?,?)",
                (announcement,timestamp,session["id"],session["name"]))
                # commit return none on successfull execution
                # and true when when combined with not and sucessfull execution occurs
                if not notice.commit():
                    return render_template("add.html",login=session,done="success")
                else:
                    return render_template("add.html",login=session,done="fail")
    else:
        return redirect("/denied")

# When announcements page is accessed
@app.route("/announcements", methods=["GET"])
def announcements():
    # if user is not logged in
    if not session:
        # Redirect to homepage
        return redirect("/denied")
    # When acessing deafult page
    if request.method == "GET":
        list = pandas.read_sql_query("SELECT * FROM notices ORDER BY id DESC",notice)
        # Converting DataFrame to List of Dicts
        list = list.to_dict("records")
        # List count for pagination
        pagination = len(list)
        pagination = pagination / 10
        # if pagination is not a int add 1 extra page
        if isinstance(pagination,float):
            pagination = int(pagination) + 1
        # if no of pages is more then 10 show only 10 pages
        if pagination > 10 :
            pagination = 10
        # if user clicked on any pagination button get its number
        try:
            page = int(request.args.get("pages"))
        except:
            page = 1
        # if delete is passed
        try:
            delete = int(request.args.get("delete"))
        except:
            delete = 0
        # Chopping the list so as to show only first 10 records
        if page < 1 or page > pagination or not page:
            page = 1
            list = list[0:10]
        else:
            list = list[((page-1)*10):(page*10)]
        # if deletion failed
        if request.args.get("delete") == "alert":
            delete = request.args.get("delete")
        # if logged in
        return render_template("announcements.html",
        login=session,notices=list,pagination=pagination,page=page,delete=delete)

# for deleting announcement
@app.route("/delete")
def delete():
    # if logged in as teacher
    if session["type"] == "teacher":
        # try to convert annoucement id to int
        try:
            id = int(request.args.get("id"))
        except:
            return redirect("/announcements?delete=alert")
        notcur.execute("DELETE FROM notices WHERE id =?",(id,))
        # commit return none on successfull execution
        # and true when when combined with not and sucessfull execution occurs
        if not notice.commit():
            return redirect("/announcements?delete=1")
        else:
            return redirect("/announcements?delete=alert")
    else:
        return redirect("/denied")

"""Contact And Messaging Section"""

# when user click on contact pages
@app.route("/contact", methods=["GET","POST"])
def announcement():
    if session:
        # if user access to send a message
        if request.method == "GET":
            return render_template("contact.html",login=session)
        # when send message button clicked
        else:
            # getting values entered by the user
            name = request.form.get("name")
            email = request.form.get("email")
            # check if annoucement id entered is an int or not
            try :
                announcement = int(request.form.get("announcement"))
            except:
                return render_template("contact.html",login=session,alert="Announcement ID Must Be A Number")
            message = request.form.get("message")
            # to check if annoucement exists or not
            announced = pandas.read_sql_query("SELECT * FROM notices WHERE id = ?",notice,params = (announcement,))
            #return render_template("contact.html",login=session,success=announced["userid"][0])
            # if annoucement doesn't exist
            if announced.empty:
                return render_template("contact.html",login=session,alert="Announcement ID Doesn't Exist")
            reciver = int(announced["userid"][0])
            # if any field was left blank
            if not message or not announcement or not email or not name:
                return render_template("contact.html",login=session,alert="All Field Must Be Provided")
            else:
                mescur.execute("INSERT INTO messages (name,sender,reciever,email,announcement,message) VALUES (?,?,?,?,?,?)",(name,session["id"],reciver,email,announcement,message))
                messagesdb.commit()
                return render_template("contact.html",login=session,success="Message Sent, You Will Be Shortly Contacted On You E-Mail")
    else:
        return redirect("/denied")

# for cheking messages
@app.route("/messages", methods = ["GET", "POST"])
def messages():
    # if user not logged in as teacher
    if session["type"] == "student":
        return redirect("/denied")
    # when requested the page via get
    if request.method == "GET":
        # to load messages
        messages = pandas.read_sql_query("SELECT * FROM messages WHERE reciever = ? ORDER BY id DESC",messagesdb,params = (session["id"],))
        # Converting DataFrame to List of Dicts
        messages = messages.to_dict("records")
        # message count for pagination
        pagination = len(messages)
        pagination = pagination / 10
        # if pagination is not a int add 1 extra page
        if isinstance(pagination,float):
            pagination = int(pagination) + 1
        # if no of pages is more then 10 show only 10 pages
        if pagination > 10 :
            pagination = 10
        # if user clicked on any pagination button get its number
        try:
            page = int(request.args.get("pages"))
        except:
            page = 1
        # if delete is passed
        try:
            deletemessage = int(request.args.get("deletemessage"))
        except:
            deletemessage = 0
        # Chopping the list so as to show only first 10 records
        if page < 1 or page > pagination or not page:
            page = 1
            messages = messages[0:10]
        else:
            messages = messages[((page-1)*10):(page*10)]
        # if deletion failed
        if request.args.get("deletemessage") == "alert":
            deletemessage = request.args.get("deletemessage")
        # getting announcments
        for message in messages:
            announcement = pandas.read_sql_query("SELECT * FROM notices where id = ?;",notice,params=(message["announcement"],))
            # replacing annoucement id in the dict bu actual announcement
            message["announcement"] = announcement["announcement"][0]
        # if logged in
        return render_template("messages.html",
        login=session,messages=messages,pagination=pagination,page=page,delete=deletemessage)

# for deleting messages
@app.route("/deletemessage")
def deletemessage():
    # if logged in as teacher
    if session["type"] == "teacher":
        # try to convert message id to int
        try:
            id = int(request.args.get("id"))
        except:
            return redirect("/messages?deletemessage=alert")
        mescur.execute("DELETE FROM messages WHERE id =?",(id,))
        # commit return none on successfull execution
        # and true when when combined with not and sucessfull execution occurs
        if not messagesdb.commit():
            return redirect("/messages?deletemessage=1")
        else:
            return redirect("/messages?deletemessage=alert")
    else:
        return redirect("/denied")

"""Exception Handling Section"""

# When user tires to access something he shouldn't
@app.route("/denied")
def denied():
    # when logged in
    if session :
        # converting the first character of account type to capital
        type=session["type"][0].upper() + (session["type"][1:])
        return render_template("denied.html",login=session,type=type)
    # when not logged in
    else:
        return render_template("denied.html",login=session)

# When user is logged in tries to access non-logged pages
@app.route("/logged")
def logged():
    # when logged in
        return render_template("logged.html",login=session)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html',login=session), 404
