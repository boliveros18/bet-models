# utils/filters.py
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from .data_loader import data_loader

class EventFilter:
    def __init__(self):
        self.all_events = data_loader.get_all_events()
    
    def filter_by_date(self, events: List[Dict], date_str: str) -> List[Dict]:
        if not date_str:
            return events
        try:
            filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            return [e for e in events if e.get("date_str") == date_str]
        except ValueError:
            return events
    
    def filter_by_date_range(self, events: List[Dict], start_date: str, end_date: str) -> List[Dict]:
        if not start_date and not end_date:
           return events
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            filtered = []
            for event in events:
                if event.get("datetime_obj"):
                    event_date = event["datetime_obj"].date()
                    if start and event_date < start:
                        continue
                    if end and event_date > end:
                        continue
                    filtered.append(event)
            return filtered
        except ValueError:
            return events
    
    def filter_by_tournament(self, events: List[Dict], tournament_id: str) -> List[Dict]:
        if not tournament_id:
            return events
        return [e for e in events if e.get("tournament_id") == tournament_id]
    
    def filter_by_country(self, events: List[Dict], country: str) -> List[Dict]:
        if not country:
            return events
        return [e for e in events if e.get("country", "").lower() == country.lower()]
    
    def filter_by_winned(self, events: List[Dict], winned: str) -> List[Dict]:
        if not winned:
            return events
        if winned == "true":
            return [e for e in events if e.get('winned') is True]
        elif winned == "false":
            return [e for e in events if e.get('winned') is False]
        elif winned == "pending":
            return [e for e in events if e.get('winned') is None] 
        return events
    
    def filter_by_edge(self, events: List[Dict], min_edge: float, max_edge: float) -> List[Dict]:
        if min_edge is None and max_edge is None:
            return events
        filtered = events
        if min_edge is not None:
            filtered = [e for e in filtered if e.get("selected_edge", 0) >= min_edge]
        if max_edge is not None:
            filtered = [e for e in filtered if e.get("selected_edge", 0) <= max_edge]
        return filtered
    
    def filter_by_bet_type(self, events: List[Dict], bet_type: str) -> List[Dict]:
        if not bet_type:
            return events
        return [e for e in events if e.get("selected_bet") == bet_type]
    
    def apply_filters(self, 
                     date: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     tournament: Optional[str] = None,
                     country: Optional[str] = None,
                     winned: Optional[str] = None,
                     min_edge: Optional[float] = None,
                     max_edge: Optional[float] = None,
                     bet_type: Optional[str] = None) -> List[Dict]:
        events = self.all_events.copy()
        
        if date:
            events = self.filter_by_date(events, date)
        elif start_date or end_date:
            events = self.filter_by_date_range(events, start_date, end_date)
        
        if tournament:
            events = self.filter_by_tournament(events, tournament)
        if country:
            events = self.filter_by_country(events, country)
        if winned:
            events = self.filter_by_winned(events, winned)
        if min_edge is not None or max_edge is not None:
            events = self.filter_by_edge(events, min_edge, max_edge)
        if bet_type:
            events = self.filter_by_bet_type(events, bet_type)
        
        return events

filter_instance = EventFilter()