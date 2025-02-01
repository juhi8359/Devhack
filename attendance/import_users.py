from app import app, db, User
import csv

# def import_users():
#     with app.app_context():
#         with open('users.csv', 'r') as f:
#             csv_reader = csv.DictReader(f)
#             for row in csv_reader:
#                 user = User(
#                     username=row['username'],
#                     password=row['password'],  # Store plaintext temporarily (not secure long-term)
#                     role=row['role']
#                 )
#                 db.session.add(user)
#             db.session.commit()
        
def import_users():
    with app.app_context():
        with open('users.csv', 'r') as f:
            csv_reader = csv.DictReader(f)
            # for row in csv_reader:
            #     # Check if username exists
            #     existing_user = User.query.filter_by(username=row['username']).first()
            #     if not existing_user:
            #         user = User(
            #             username=row['username'],
            #             password=row['password'],
            #             role=row['role']
            #         )
            #         db.session.add(user)
            #     else:
            #         print(f"Skipping duplicate: {row['username']}")
            # db.session.commit()
            for row in csv_reader:
                existing_user = User.query.filter_by(username=row['username']).first()
                if existing_user:
                    existing_user.password = row['password']  # Update password
                    existing_user.role = row['role']          # Update role
                else:
                    user = User(username=row['username'], password=row['password'], role=row['role'])
                    db.session.add(user)
            db.session.commit()
            print("Users imported successfully!")
if __name__ == '__main__':
    import_users()