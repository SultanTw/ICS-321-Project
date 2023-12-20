from flask import Flask, render_template, request, redirect, url_for, g, session
import sqlite3
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'sultan_key'  # a secret key for security purposes

DATABASE = 'hospital_v3.db'

# def get_db():
#     db = getattr(g, '_database', None)
#     if db is None:
#         db = g._database = sqlite3.connect(DATABASE)
#     return db

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

@app.route('/')
def home():
    user_type = session.get('User_Type')  # Get type from session or return none
    print("user type is", user_type)
    if user_type == 'Admin':
        return redirect(url_for('admin_dashboard'))
    elif user_type == 'Patient':
        return redirect(url_for('patient_dashboard'))
    #If user_type is none, then user is not logged in
    return render_template('home.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        cur = db.execute('SELECT * FROM User WHERE Email = ? AND Password = ?', (email, password))
        user = cur.fetchone() # this method returns one row from the query result
        if user:
            session['SSN'] = user['SSN']  # User's id
            session['Name'] = user['Name']  # User's name
            session['User_Type'] = user['User_Type']  # User's type
            return redirect(url_for('home'))
        else: # User not found
            error = "Invalid email or password!" 
    return render_template('login.html', error=error)



@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('User_Type') != 'Admin':
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html' , user_name=session.get('Name', ''))


@app.route('/patient_dashboard')
def patient_dashboard():
    if session.get('User_Type') != 'Patient':
        return redirect(url_for('home'))
    
    # get user from db
    db = get_db()
    user_id = session.get('SSN')
    cur = db.execute('SELECT * FROM User WHERE SSN= ?', (user_id,))
    user = dict(cur.fetchone())


    return render_template('patient_dashboard.html', user=user)





@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':

        #add to new dict and check if all if "" then make None
        new_dict = {}
        for key in request.form:
            if request.form[key] == "" or request.form[key] == "None":
                new_dict[key] = None
            else:
                new_dict[key] = request.form[key]

        


        name = new_dict['name']
        email = new_dict['email']
        password = new_dict['password']
        contact_number = new_dict['contact_number']
        dob = new_dict['dob']
        medical_history = new_dict['medical_history']
        blood_type = new_dict['blood_type']
        weight = new_dict['weight']
        height = new_dict['height']

        
        

        db = get_db()
        cur = db.execute('SELECT * FROM User WHERE Email = ?', (email,))
        user = cur.fetchone() 

        if user:
            error = "Email already registered!"
        else:
            blood_type_id = blood_type_name_to_id(blood_type)
            db.execute('INSERT INTO User (Name, Email, Password, Contact_Number, Date_Of_Birth, Medical_History, Blood_Type, Weight, Height) VALUES (?, ?, ?, ?, ?, ?, ?,?,?)', 
                       (name, email, password,contact_number,  dob, medical_history,blood_type_id, weight, height))
            db.commit()
            session['Name'] = name
            session['SSN'] = db.execute('SELECT SSN FROM User WHERE Email = ?', (email,)).fetchone()[0]
            session['User_Type'] = 'Patient'
            return redirect(url_for('home'))

    return render_template('register.html', error=error)




@app.route('/manage_patients', methods=['GET', 'POST'])
def manage_users():
    # Logic to retrieve and display all users with their blood types
    db = get_db()
    cur = db.execute('SELECT User.*, Blood_Type.Type AS Blood_Type_Name FROM User JOIN Blood_Type ON User.Blood_Type = Blood_Type.Blood_Type_ID WHERE User.User_Type = ?', ('Patient',))
    users = cur.fetchall()
    return render_template('manage_patients.html', users=users)



@app.route('/add_patient', methods=['POST'])
def add_patient():
    if session['User_Type'] != 'Admin':
        return redirect(url_for('home'))
    # Logic to add a new user

    new_dict = {}
    for key in request.form:
        if request.form[key] == "":
            new_dict[key] = None
        else:
            new_dict[key] = request.form[key]

    db = get_db()
    name = new_dict['name']
    email = new_dict['email']
    contact_number = new_dict['contact_number']
    dob = new_dict['dob']
    medical_history = new_dict['medical_history']
    blood_type = new_dict['blood_type']
    blood_type_id = blood_type_name_to_id(blood_type)
    weight = new_dict['weight']
    height = new_dict['height']

    error = None
    try:
        db.execute('INSERT INTO User (Name, Email, Contact_Number, Date_Of_Birth, Medical_History, Blood_Type, Weight, Height) VALUES (?, ?, ?, ?, ?, ?,?,?)', 
                    (name, email, contact_number,  dob, medical_history,blood_type_id, weight, height))
        db.commit()
        return redirect(url_for('manage_users'))
    except Exception as e:
        error = "An error occurred while adding the user."
        print(e)

    return render_template('manage_patients.html', error=error)



def blood_type_name_to_id(blood_type):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT Blood_Type_ID FROM Blood_Type WHERE Type = ?', (blood_type,))
    blood_type_id = cursor.fetchone()[0]
    return blood_type_id

def blood_type_id_to_name(blood_type_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT Type FROM Blood_Type WHERE Blood_Type_ID = ?', (blood_type_id,))
    blood_type = cursor.fetchone()[0]
    return blood_type


@app.route('/edit_patient/<int:user_id>', methods=['GET', 'POST'])
def edit_patient(user_id):
    if session['User_Type'] != 'Admin':
        return redirect(url_for('home'))
    print('REQUEST METHOD IS ', request.method)
    if request.method == 'POST':
        
        new_dict = {}
        for key in request.form:
            if request.form[key] == "" or request.form[key] == "None":
                new_dict[key] = None
            else:
                new_dict[key] = request.form[key]

        error = None
        db = get_db()
        name = new_dict['name']
        email = new_dict['email']
        dob = new_dict['dob']
        contact_number = new_dict['contact_number']
        medical_history = new_dict['medical_history']
        blood_type = new_dict['blood_type']
        blood_type_id = blood_type_name_to_id(blood_type)
        print('BLOOD TYPE IS ', blood_type_id)
        weight = new_dict['weight']
        height = new_dict['height']
        print((name, email, dob, blood_type, weight, height, user_id))
        try: 
            db.execute('UPDATE User SET Name=?, Email=?, Date_Of_Birth=?, Blood_Type=?, Weight=?, Height=?, Contact_Number=?, Medical_History=? WHERE SSN=?', 
                        (name, email, dob, blood_type_id, weight, height,contact_number, medical_history, user_id))
            db.commit()
            return redirect(url_for('manage_users'))
        except Exception as e:
            error = "Error: Please check all inputs."
            print(e)
            cur = db.execute('SELECT * FROM User WHERE SSN= ?', (user_id,))
            user = dict(cur.fetchone())  # Convert sqlite3.Row to dictionary
            user['Blood_Type'] = blood_type_id_to_name(user['Blood_Type'])
            return render_template('edit_patient.html', error=error, user=user)
    # Logic to retrieve and display a user
    db = get_db()
    cur = db.execute('SELECT * FROM User WHERE SSN= ?', (user_id,))
    user = dict(cur.fetchone())  # Convert sqlite3.Row to dictionary
    user['Blood_Type'] = blood_type_id_to_name(user['Blood_Type'])
    print(user)
    return render_template('edit_patient.html', user=user)


@app.route('/delete_patient/<int:user_id>', methods=['POST'])
def delete_patient(user_id):
    if request.method == 'GET':
        return redirect(url_for('manage_users'))
    if session['User_Type'] != 'Admin':
        return redirect(url_for('home'))
    

    # Logic to delete a user
    db = get_db()
    db.execute('DELETE FROM User WHERE SSN = ?', (user_id,))
    db.commit()
    return redirect(url_for('manage_users'))




@app.route('/view_history', methods=['GET', 'POST'])
def view_history():
    user_id = session.get('SSN')  # Assuming user_id is stored in session

    # Retrieve user's donation history from the database
    db = get_db()
    query = f"""
           SELECT 
    P.Name AS Receiver_Name, 
    P.Contact_Number AS Receiver_Contact_Number, 
    BT.Type AS Receiver_Blood_Type_Name, 
    D.Date AS Receiving_Date, 
    COUNT(BBI.Blood_Bag_ID) AS Number_of_bags_used, 
    SUM(BB.Volume) AS Total_Blood_Volume_Received
FROM 
    Donations D
    JOIN User P ON D.Recipient_ID = P.SSN
    JOIN Blood_Bag_IDs BBI ON D.Donations_ID = BBI.Donation_ID
    JOIN Blood_Bag BB ON BBI.Blood_Bag_ID = BB.Blood_Bag_ID
    JOIN Blood_Type BT ON P.Blood_Type = BT.Blood_Type_ID
WHERE 
    P.SSN = {user_id}
GROUP BY 
    D.Donations_ID;

            """
    cur = db.execute(query)
    user_recievings = cur.fetchall()


    donations_query = f"""
            SELECT 
    p_donor.Name,
    p_donor.Contact_Number,
    bt.Type as Patient_Blood_Type_Name,
    bb.Expiry_Date,
    bb.Volume as Bag_Volume,
    p_receiver.Name as Receiver_Name,
    bb.Is_Valid
FROM 
    User p_donor
JOIN 
    Blood_Bag bb ON p_donor.SSN = bb.Donor_ID
JOIN 
    Blood_Type bt ON p_donor.Blood_Type = bt.Blood_Type_ID
LEFT JOIN 
    Blood_Bag_IDs bbi ON bb.Blood_Bag_ID = bbi.Blood_Bag_ID
LEFT JOIN 
    Donations d ON bbi.Donation_ID = d.Donations_ID
LEFT JOIN 
    User p_receiver ON d.Recipient_ID = p_receiver.SSN
WHERE 
    p_donor.SSN = {user_id};
            """
    
    # print all recievings 
    for row in user_recievings:
        print("RECIEVING IS:  ", row['Total_Blood_Volume_Received'])

    user_donations = db.execute(donations_query).fetchall()

    return render_template('view_history.html',  
                           user_recievings=user_recievings
                           ,user_donations=user_donations)



@app.route('/view_history_admin', methods=['GET', 'POST'])
def view_history_admin():


    


    
    # Retrieve user's donation history from the database
    db = get_db()
    all_snn = db.execute('SELECT SSN FROM User').fetchall()
    all_snn = [str(x['SSN']) for x in all_snn]
    query = f"""
            SELECT
    P.SSN,
    P.Name AS Receiver_Name, 
    P.Contact_Number AS Receiver_Contact_Number, 
    BT.Type AS Receiver_Blood_Type_Name, 
    D.Date AS Receiving_Date, 
    COUNT(BBI.Blood_Bag_ID) AS Number_of_bags_used, 
    SUM(BB.Volume) AS Total_Blood_Volume_Received
FROM 
    Donations D
    JOIN User P ON D.Recipient_ID = P.SSN
    JOIN Blood_Bag_IDs BBI ON D.Donations_ID = BBI.Donation_ID
    JOIN Blood_Bag BB ON BBI.Blood_Bag_ID = BB.Blood_Bag_ID
    JOIN Blood_Type BT ON P.Blood_Type = BT.Blood_Type_ID
GROUP BY 
    D.Donations_ID;
            """
    

    if request.method == 'POST' and request.form['ssn'] in all_snn:
        filtering_ssn = request.form['ssn']
        query = f"""
            SELECT
    P.SSN,
    P.Name AS Receiver_Name,
    P.Contact_Number AS Receiver_Contact_Number,
    BT.Type AS Receiver_Blood_Type_Name,
    D.Date AS Receiving_Date,
    COUNT(BBI.Blood_Bag_ID) AS Number_of_bags_used,
    SUM(BB.Volume) AS Total_Blood_Volume_Received
FROM
    Donations D
    JOIN User P ON D.Recipient_ID = P.SSN
    JOIN Blood_Bag_IDs BBI ON D.Donations_ID = BBI.Donation_ID
    JOIN Blood_Bag BB ON BBI.Blood_Bag_ID = BB.Blood_Bag_ID
    JOIN Blood_Type BT ON P.Blood_Type = BT.Blood_Type_ID
WHERE
    P.SSN = {filtering_ssn}
GROUP BY
    D.Donations_ID;
            """
    

    cur = db.execute(query)
    user_recievings = cur.fetchall()


    donations_query = f"""
            SELECT 
    P_donor.SSN,
    p_donor.Name,
    p_donor.Contact_Number,
    bt.Type as Patient_Blood_Type_Name,
    bb.Expiry_Date,
    bb.Volume as Bag_Volume,
    p_receiver.Name as Receiver_Name,
    bb.Is_Valid
FROM 
    User p_donor
JOIN 
    Blood_Bag bb ON p_donor.SSN = bb.Donor_ID
JOIN 
    Blood_Type bt ON p_donor.Blood_Type = bt.Blood_Type_ID
LEFT JOIN 
    Blood_Bag_IDs bbi ON bb.Blood_Bag_ID = bbi.Blood_Bag_ID
LEFT JOIN 
    Donations d ON bbi.Donation_ID = d.Donations_ID
LEFT JOIN 
    User p_receiver ON d.Recipient_ID = p_receiver.SSN
            """
    
    if request.method == 'POST' and request.form['ssn'] in all_snn:
        filtering_ssn = request.form['ssn']
        donations_query = f"""
            SELECT
    P_donor.SSN,
    p_donor.Name,
    p_donor.Contact_Number,
    bt.Type as Patient_Blood_Type_Name,
    bb.Expiry_Date,
    bb.Volume as Bag_Volume,
    p_receiver.Name as Receiver_Name,
    bb.Is_Valid
FROM
    User p_donor
JOIN
    Blood_Bag bb ON p_donor.SSN = bb.Donor_ID
JOIN    
    Blood_Type bt ON p_donor.Blood_Type = bt.Blood_Type_ID
LEFT JOIN   
    Blood_Bag_IDs bbi ON bb.Blood_Bag_ID = bbi.Blood_Bag_ID
LEFT JOIN   
    Donations d ON bbi.Donation_ID = d.Donations_ID
LEFT JOIN   
    User p_receiver ON d.Recipient_ID = p_receiver.SSN
WHERE   
    P_donor.SSN = {filtering_ssn};
            """
    
    # print all recievings 
    for row in user_recievings:
        print("RECIEVING IS:  ", row['Total_Blood_Volume_Received'])


    user_donations = db.execute(donations_query).fetchall()

    return render_template('view_history_admin.html',  
                           user_recievings=user_recievings
                           ,user_donations=user_donations)







@app.route('/donate_blood', methods=['GET', 'POST'])
def donate_blood():
    user_id = session.get('SSN')

    # if post 
    if request.method == 'POST':
        print("POST")
        db = get_db()
        # get user info
        cur = db.execute('SELECT * FROM User WHERE SSN = ?', (user_id,))
        user = cur.fetchone() # this method returns one row from the query result
        # get user accurate age (calculate even the months)
        user_age = datetime.datetime.now().year - int(user['Date_Of_Birth'][:4])
        if datetime.datetime.now().month < int(user['Date_Of_Birth'][5:7]):
            user_age -= 1
        elif datetime.datetime.now().month == int(user['Date_Of_Birth'][5:7]) and datetime.datetime.now().day < int(user['Date_Of_Birth'][8:10]):
            user_age -= 1
        # check if user is eligible to donate
            

        if user['Weight'] < 51 or user_age < 17 or user['Medical_History'] != None:
            return render_template('donate_blood.html', user_id=user_id, error="You are not eligible to donate blood.")

        # get blood type id
        blood_type_id = user['Blood_Type']
        

        volume = int(request.form['liters'])
        
        #use datetime to make expiry date be 2 months from now
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=60)
        expiry_date = expiry_date.strftime("%Y-%m-%d")


        #each bag is 450 ml, this divides the volume into bags
        blood_bags = []
        while volume >= 450:
            blood_bags.append(450)
            volume -= 450
        if volume > 0:
            blood_bags.append(volume)

        error = None
        try:
            for blood_bag in blood_bags:
                db.execute('INSERT INTO Blood_Bag (Volume, Blood_Type_ID, Expiry_Date, Donor_ID, Is_Valid) VALUES (?, ?, ?, ?,?)', 
                            (blood_bag, blood_type_id,expiry_date, user_id,1))
            db.commit()
            return redirect(url_for('view_history', thanks=True))  # Add 'thanks=True' to include the thanks parameter in the URL
        except Exception as e:
            error = "An error occurred while adding the user."
            print(e)
            return render_template('donate_blood.html', error=error, user_id=user_id)

    return render_template('donate_blood.html', user_id=user_id)




@app.route('/update_user_info', methods=['GET', 'POST'])
def update_user_info():
    if session['User_Type'] != 'Patient':
        return redirect(url_for('home'))
    print('REQUEST METHOD IS ', request.method)
    if request.method == 'POST':
            
            
            new_dict = {}
            for key in request.form:
                if request.form[key] == "" or request.form[key] == "None":
                    new_dict[key] = None
                else:
                    new_dict[key] = request.form[key]     

           

            # Logic to edit a user
            error = None
            db = get_db()
            user_id = session.get('SSN')
            name = new_dict['name']
            email = new_dict['email']
            dob = new_dict['dob']
            contact_number = new_dict['contact_number']
            medical_history = new_dict['medical_history']
            blood_type = new_dict['blood_type']
            blood_type_id = blood_type_name_to_id(blood_type)
            print('BLOOD TYPE IS ', blood_type_id)
            weight = new_dict['weight']
            height = new_dict['height']
            print((name, email, dob, blood_type, weight, height, user_id))
            try: 
                db.execute('UPDATE User SET Name=?, Email=?, Date_Of_Birth=?, Blood_Type=?, Weight=?, Height=?, Contact_Number=?, Medical_History=? WHERE SSN=?', 
                            (name, email, dob, blood_type_id, weight, height,contact_number, medical_history, user_id))
                db.commit()
                return redirect(url_for('patient_dashboard'))
            except Exception as e:
                error = "Error: Please check all inputs."
                print(e)
                cur = db.execute('SELECT * FROM User WHERE SSN= ?', (user_id,))
                user = dict(cur.fetchone())  # Convert sqlite3.Row to dictionary
                user['Blood_Type'] = blood_type_id_to_name(user['Blood_Type'])
                return render_template('edit_patient.html', error=error, user=user)
    # Logic to retrieve and display a user
    db = get_db()
    user_id = session.get('SSN')
    cur = db.execute('SELECT * FROM User WHERE SSN= ?', (user_id,))
    user = dict(cur.fetchone())  # Convert sqlite3.Row to dictionary
    user['Blood_Type'] = blood_type_id_to_name(user['Blood_Type'])
    print(user)
    return render_template('update_user_info.html', user=user)




@app.route('/request_blood', methods=['POST', 'GET'])
def request_blood():
    if request.method == 'POST':
        requested_bags = request.form.getlist('requested_bags')
        user_id = session.get('SSN')  # Ensure this is the correct session key for the user's ID
        
        for bag_id in requested_bags:
            # mark them as pending
            db = get_db()
            db.execute('UPDATE Blood_Bag SET Pending_By = ? WHERE Blood_Bag_ID = ?', (user_id,bag_id,))
            db.commit()
        return redirect(url_for('patient_dashboard'))
    
    else:
        # Retrieve all blood bags from the database
        db = get_db()
        cur = db.execute(f"""SELECT bb.Blood_Bag_ID, 
       bb.Volume, 
       bt.Type AS Blood_Type_Name, 
       bb.Expiry_Date, 
       u.Name AS Donor_Name,
       (bb.Volume * 5) AS Price  -- Assuming $50 per unit volume
FROM Blood_Bag bb
JOIN Blood_Type bt ON bb.Blood_Type_ID = bt.Blood_Type_ID
JOIN User u ON bb.Donor_ID = u.SSN
JOIN Blood_Compatibility bc ON bt.Blood_Type_ID = bc.Donor_Type_ID
JOIN (
    SELECT Blood_Type FROM User WHERE SSN = {session.get('SSN')}
) AS user_bt ON bc.Recipient_Type_ID = user_bt.Blood_Type
WHERE bb.Expiry_Date > CURRENT_DATE AND bb.Is_Valid = 1 AND bb.Pending_By IS NULL;
""")
        blood_bags = cur.fetchall()
        return render_template('request_blood.html', blood_bags=blood_bags)

def send_email(recipient_email, subject, message):
    sender_email = "bloodbank.ics321@gmail.com"
    sender_password = "kiti tiks gvtk ewsl"
    # Create a multipart message
    email_message = MIMEMultipart()
    email_message["From"] = sender_email
    email_message["To"] = recipient_email
    email_message["Subject"] = subject

    # Add message body
    email_message.attach(MIMEText(message, "plain"))

    # Create SMTP session
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        # Start TLS for security
        smtp.starttls()

        # Login to the email account
        smtp.login(sender_email, sender_password)

        # Send email
        smtp.send_message(email_message)


@app.route('/process_blood_requests', methods=['POST', 'GET'])
def process_blood_requests():
    if request.method == 'POST':
        action = request.form['action']

        names = []
        emails = []

        if action == 'Approve':
            db = get_db()
            # update the blood bags, set is_valid to 0
            requested_bags = request.form.getlist('requested_bags')
            requesters = {}
            for bag_id in requested_bags:
                #find out the requester id
                requester_id = db.execute('SELECT Pending_By FROM Blood_Bag WHERE Blood_Bag_ID = ?', (bag_id,)).fetchone()[0]
                #updater user balance after finding out the price from the volume
                volume = db.execute('SELECT Volume FROM Blood_Bag WHERE Blood_Bag_ID = ?', (bag_id,)).fetchone()[0]
                price = volume * 5
                db.execute('UPDATE User SET Balance = Balance - ? WHERE SSN = ?', (price, requester_id,))
                db.commit()

                # mark them as used
                db = get_db()
                db.execute('UPDATE Blood_Bag SET Is_Valid = 0 WHERE Blood_Bag_ID = ?', (bag_id,))
                db.commit()

                #add to requesters dict
                if requester_id in requesters:
                    requesters[requester_id].append(bag_id)
                else:
                    requesters[requester_id] = [bag_id]
            
            #update Donation table and bloodbagsID table via looping through requesters dict making sure to not duplicate donations, each requester has 1 donation
            db = get_db()
            for requester_id in requesters:
                #update Donation table
                db.execute('INSERT INTO Donations (Recipient_ID, Date) VALUES (?, ?)', (requester_id, datetime.datetime.now().strftime("%Y-%m-%d")))
                db.commit()

                # email them about the approved blood using send_email function and their name and email
                recipient_email = db.execute('SELECT Email FROM User WHERE SSN = ?', (requester_id,)).fetchone()[0]
                recipient_name = db.execute('SELECT Name FROM User WHERE SSN = ?', (requester_id,)).fetchone()[0]
                names.append(recipient_name)
                emails.append(recipient_email)
                subject = "Blood Request Approved"
                message = f"Dear {recipient_name},\n\nYour blood request has been approved. Please visit the hospital to receive your blood.\n\nRegards,\nICS321 Blood Bank"
                print("EMAIL IS ", recipient_email)
                print("Name IS ", recipient_name)
                print("Subject IS ", subject)
                print("Message IS ", message)
                send_email(recipient_email, subject, message)


                #update Blood_Bag_IDs table
                donation_id = db.execute('SELECT Donations_ID FROM Donations WHERE Recipient_ID = ? ORDER BY Donations_ID DESC LIMIT 1', (requester_id,)).fetchone()[0]
                for bag_id in requesters[requester_id]:
                    db.execute('INSERT INTO Blood_Bag_IDs (Donation_ID, Blood_Bag_ID) VALUES (?, ?)', (donation_id, bag_id,))
                    db.commit()

            
            
        else: # if action is reject
            # update the blood bags, set pending_by to null
            requesters = {}
            requested_bags = request.form.getlist('requested_bags')
            db = get_db()
            for bag_id in requested_bags:
                requester_id = db.execute('SELECT Pending_By FROM Blood_Bag WHERE Blood_Bag_ID = ?', (bag_id,)).fetchone()[0]
                # mark them as pending
                db = get_db()
                db.execute('UPDATE Blood_Bag SET Pending_By = NULL WHERE Blood_Bag_ID = ?', (bag_id,))
                db.commit()

                #add to requesters dict
                if requester_id in requesters:
                    requesters[requester_id].append(bag_id)
                else:
                    requesters[requester_id] = [bag_id]
            
            # email them about the rejected blood using send_email function and their name and email
            db = get_db()
            for requester_id in requesters:
                recipient_email = db.execute('SELECT Email FROM User WHERE SSN = ?', (requester_id,)).fetchone()[0]
                recipient_name = db.execute('SELECT Name FROM User WHERE SSN = ?', (requester_id,)).fetchone()[0]
                names.append(recipient_name)
                emails.append(recipient_email)
                subject = "Blood Request Rejected"
                message = f"Dear {recipient_name},\n\nYour blood request has been rejected. Please contact the hospital for more information.\n\nRegards,\nICS321 Blood Bank"
                send_email(recipient_email, subject, message)

                
        return redirect(url_for('process_blood_requests'))

    

    query = f"""SELECT 
    BB.Blood_Bag_ID, 
    pending_user.Name AS Pending_By,  -- Alias for the user who requested the blood bag
    BB.Pending_By AS Pending_By_ID,       -- ID of the user who requested the blood bag
    BB.Volume, 
    BT.Type AS Blood_Type_Name,         -- Alias for blood type name
    BB.Expiry_Date, 
    donor_user.Name AS Donor_Name,          -- Alias for the donor's name
    (BB.Volume * 5) AS Price                -- Calculated price based on volume
FROM 
    Blood_Bag BB
JOIN 
    Blood_Type BT ON BB.Blood_Type_ID = BT.Blood_Type_ID
JOIN 
    User donor_user ON BB.Donor_ID = donor_user.SSN  -- Alias for donor
LEFT JOIN 
    User pending_user ON BB.Pending_By = pending_user.SSN  -- Alias for pending user
WHERE 
    BB.Is_Valid = 1   
    AND BB.Pending_By IS NOT NULL;  -- Only show pending blood bags
    """

    db = get_db()
    cur = db.execute(query)
    blood_bags = cur.fetchall()
    return render_template('process_blood_requests.html', blood_bags=blood_bags)
    



# @app.teardown_appcontext
# def close_connection(exception):
#     db = getattr(g, '_database', None)
#     if db is not None:
#         db.close()




@app.route('/add_balance', methods=['GET', 'POST'])
def add_balance():
    if session['User_Type'] != 'Patient':
        return redirect(url_for('home'))
    if request.method == 'POST':
        # Logic to edit a user
        error = None
        db = get_db()
        user_id = session.get('SSN')
        amount = request.form['amount']
        if amount == '':
            amount = 0
        amount = float(amount)

        try: 

            if amount < 0:
                error = "Error: Please enter a positive amount."
                raise Exception(error)
            
            db.execute('UPDATE User SET Balance = Balance + ? WHERE SSN=?', 
                        (amount, user_id))
            db.commit()
            return redirect(url_for('patient_dashboard'))
        except Exception as e:
            error = "Error: Please check all inputs."
            print(e)
            cur = db.execute('SELECT * FROM User WHERE SSN= ?', (user_id,))
            user = dict(cur.fetchone())
            return render_template('add_balance.html', error=error, user=user)
    # Logic to retrieve and display a user
    db = get_db()
    user_id = session.get('SSN')
    cur = db.execute('SELECT * FROM User WHERE SSN= ?', (user_id,))
    user = dict(cur.fetchone())
    return render_template('add_balance.html', user=user)


@app.route('/generate_reports')
def generate_reports():
    if session['User_Type'] != 'Admin':
        return redirect(url_for('home'))
    return render_template('generate_reports.html')


@app.route('/report_blood_types')
def report_blood_types():
    if session['User_Type'] != 'Admin':
        return redirect(url_for('home'))
    db = get_db()
    query = """
    SELECT 
    BT.Type AS Blood_Type_Name,
    COUNT(BB.Blood_Bag_ID) AS Total_Bags_Amount,
    SUM(BB.Volume) AS Total_Bags_Volume
FROM 
    Blood_Bag BB
    JOIN Blood_Type BT ON BB.Blood_Type_ID = BT.Blood_Type_ID
WHERE 
    BB.Is_Valid = 1 AND BB.Pending_By IS NULL
GROUP BY 
    BT.Type;

"""
    cur = db.execute(query)
    blood_types = cur.fetchall()
    return render_template('report_blood_types.html', blood_types=blood_types)



@app.route('/report_payments')
def report_payments():
    if session['User_Type'] != 'Admin':
        return redirect(url_for('home'))
    db = get_db()
    query = """
SELECT 
    P.Name AS Receiver_Name, 
    P.Contact_Number AS Receiver_Contact_Number, 
    BT.Type AS Receiver_Blood_Type_Name, 
    D.Date AS Receiving_Date, 
    COUNT(BBI.Blood_Bag_ID) AS Number_of_bags_used, 
    SUM(BB.Volume) AS Total_Blood_Volume_Received,
    SUM(BB.Volume) * 5 AS Total_Payment
FROM 
    Donations D
    JOIN User P ON D.Recipient_ID = P.SSN
    JOIN Blood_Bag_IDs BBI ON D.Donations_ID = BBI.Donation_ID
    JOIN Blood_Bag BB ON BBI.Blood_Bag_ID = BB.Blood_Bag_ID
    JOIN Blood_Type BT ON P.Blood_Type = BT.Blood_Type_ID
GROUP BY 
    D.Donations_ID;
"""
    cur = db.execute(query)
    payments = cur.fetchall()
    return render_template('report_payments.html', payments=payments)


@app.route('/report_blood_donations')
def report_blood_donations():
    if session['User_Type'] != 'Admin':
        return redirect(url_for('home'))
    db = get_db()
    query = """
            SELECT 
    BB.Blood_Bag_ID AS Bag_ID,
    D.Name,
    D.Contact_Number,
    BT.Type AS Donor_Blood_Type_Name,
    BB.Expiry_Date AS Bag_Expiry_Date,
    DATE(BB.Expiry_Date, '-60 days') AS Bag_Donation_Date,
    BB.Volume AS Bag_Volume,
    R.Name AS Receiver_Name
FROM 
    Blood_Bag BB
    LEFT JOIN User D ON BB.Donor_ID = D.SSN  -- Join with Donor
    LEFT JOIN Blood_Type BT ON BB.Blood_Type_ID = BT.Blood_Type_ID
    LEFT JOIN Donations DN ON DN.Donations_ID = (SELECT Donation_ID FROM Blood_Bag_IDs WHERE Blood_Bag_ID = BB.Blood_Bag_ID)
    LEFT JOIN User R ON DN.Recipient_ID = R.SSN  -- Join with Recipient
WHERE 
    DATE(BB.Expiry_Date, '-60 days') >= DATE('now', '-1 month')  -- Donations from the past month
ORDER BY 
    BB.Expiry_Date DESC;

            """
    cur = db.execute(query)
    month_donations = cur.fetchall()

    query = """
            SELECT 
    BB.Blood_Bag_ID AS Bag_ID,
    D.Name,
    D.Contact_Number,
    BT.Type AS Donor_Blood_Type_Name,
    BB.Expiry_Date AS Bag_Expiry_Date,
    DATE(BB.Expiry_Date, '-60 days') AS Bag_Donation_Date,
    BB.Volume AS Bag_Volume,
    R.Name AS Receiver_Name
FROM 
    Blood_Bag BB
    LEFT JOIN User D ON BB.Donor_ID = D.SSN  -- Join with Donor
    LEFT JOIN Blood_Type BT ON BB.Blood_Type_ID = BT.Blood_Type_ID
    LEFT JOIN Donations DN ON DN.Donations_ID = (SELECT Donation_ID FROM Blood_Bag_IDs WHERE Blood_Bag_ID = BB.Blood_Bag_ID)
    LEFT JOIN User R ON DN.Recipient_ID = R.SSN  -- Join with Recipient
WHERE 
    DATE(BB.Expiry_Date, '-60 days') >= DATE('now', '-7 days')  -- Donations from the past month
ORDER BY 
    BB.Expiry_Date DESC;

            """
    cur = db.execute(query)
    week_donations = cur.fetchall()
    return render_template('report_blood_donations.html', month_donations=month_donations, week_donations=week_donations)




@app.route('/guest_dashboard')
def guest_dashboard():
    return render_template('guest_dashboard.html')

@app.route('/guest_error')
def guest_error():
    return render_template('guest_error.html')



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))



if __name__ == '__main__':
    app.run(debug=True)
