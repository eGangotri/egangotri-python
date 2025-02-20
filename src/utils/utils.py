def format_time_taken(time_taken):
    if time_taken < 60:
        return f"{time_taken:.2f} seconds"
    elif time_taken < 3600:
        return f"{time_taken / 60:.2f} minutes"
    else:
        return f"{time_taken / 3600:.2f} hours"