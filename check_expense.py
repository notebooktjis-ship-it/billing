from app import app, db, Expense
with app.app_context():
    print('Expense count:', Expense.query.count())
    expenses = Expense.query.all()
    for e in expenses:
        print(f'ID: {e.id}, Category: {e.category}, Amount: {e.amount}')
