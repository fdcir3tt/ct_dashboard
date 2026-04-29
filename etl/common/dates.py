from datetime import datetime,timezone,timedelta


def date_interval(reference_date:datetime,days:int)->tuple[datetime,datetime]:
    """
    
    """
    time_difference = abs(days)
    
    if days <0:
        start = reference_date - timedelta(days=time_difference)
        end = reference_date
    else:
        start = reference_date
        end = reference_date + timedelta(days=time_difference)
    interval = (start,end)
    return interval

def date(date_str:str)->datetime:
    if date_str=="today":
        return datetime.today()
    year,month,day = date_str.split('-')
    
    return datetime(int(year),int(month),int(day),tzinfo=timezone.utc)