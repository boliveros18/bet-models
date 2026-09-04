# utils/data_loader.py
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataLoader:
    _instance = None
    _data = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._data is None:
            self.load_data()
    
    def load_data(self, file_path: str = None):
        if file_path is None:
            # Directorio donde está este archivo (utils/)
            script_dir = Path(__file__).resolve().parent
            # Directorio padre de utils/ → app/ (donde están app.py y bet_leagues.json)
            app_dir = script_dir.parent

            # Posibles ubicaciones (ordenadas por prioridad)
            candidates = [
                app_dir / "bet_leagues.json",               # app/bet_leagues.json
                app_dir / "data" / "bet_leagues.json",      # app/data/bet_leagues.json
                Path("data") / "bet_leagues.json",          # ./data/bet_leagues.json (ruta relativa)
                Path("bet_leagues.json"),                   # ./bet_leagues.json (actual)
                app_dir.parent / "data" / "bet_leagues.json" # proyecto/data/bet_leagues.json
            ]

            for candidate in candidates:
                if candidate.exists():
                    file_path = candidate
                    logger.info(f"✅ Archivo encontrado: {file_path}")
                    break

            if file_path is None:
                logger.error("❌ No se encontró bet_leagues.json en ninguna ubicación")
                self._data = {"tournaments": {}}
                return

        # Carga del archivo (sin cambios)
        try:
            if isinstance(file_path, str):
                file_path = Path(file_path)

            if not file_path.exists():
                logger.error(f"Archivo no encontrado: {file_path}")
                self._data = {"tournaments": {}}
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
            logger.info(f"✅ Datos cargados exitosamente desde {file_path}")
            logger.info(f"   Torneos encontrados: {len(self._data.get('tournaments', {}))}")

        except Exception as e:
            logger.error(f"Error al cargar datos: {e}")
            self._data = {"tournaments": {}}
    
    def get_tournaments(self) -> Dict[str, Any]:
        return self._data.get("tournaments", {})
    
    def get_tournament(self, tournament_id: str) -> Optional[Dict[str, Any]]:
        tournaments = self.get_tournaments()
        return tournaments.get(tournament_id)
    
    def get_all_events(self) -> List[Dict[str, Any]]:
        all_events = []
        tournaments = self.get_tournaments()
        
        for tournament_id, tournament_data in tournaments.items():
            tournament_name = tournament_data.get("name", "unknown")
            country = tournament_data.get("country", "unknown")
            
            for run_timestamp, run_data in tournament_data.get("prediction_runs", {}).items():
                events = run_data.get("event_bet", {})
                model_stats = run_data.get("model_stats", {})
                
                for event_id, event_data in events.items():
                    try:
                        event_datetime = datetime.fromisoformat(event_data.get("datetime", ""))
                    except:
                        event_datetime = None
                    
                    event_with_metadata = {
                        **event_data,
                        "tournament_id": tournament_id,
                        "tournament_name": tournament_name,
                        "country": country,
                        "run_timestamp": run_timestamp,
                        "event_id": event_id,
                        "model_stats": model_stats,
                        "datetime_obj": event_datetime,
                        "date_str": event_datetime.strftime("%Y-%m-%d") if event_datetime else "",
                        "winned": event_data.get("winned")  
                    }
                    all_events.append(event_with_metadata)
        
        return all_events
    
    def get_all_runs(self) -> List[Dict[str, Any]]:
        """Retorna todas las ejecuciones de modelos con estadísticas corregidas"""
        all_runs = []
        tournaments = self.get_tournaments()
        
        for tournament_id, tournament_data in tournaments.items():
            tournament_name = tournament_data.get("name", "unknown")
            country = tournament_data.get("country", "unknown")
            
            for run_timestamp, run_data in tournament_data.get("prediction_runs", {}).items():
                events = run_data.get("event_bet", {})
                model_stats = run_data.get("model_stats", {})
                
                total_events = len(events)
                winned_events = sum(1 for e in events.values() if e.get('winned') is True)
                lost_events = sum(1 for e in events.values() if e.get('winned') is False)
                pending_events = sum(1 for e in events.values() if 'winned' not in e)
                
                decided_events = winned_events + lost_events
                win_rate = winned_events / decided_events if decided_events > 0 else 0
                
                edges = [e.get('selected_edge', 0) for e in events.values() if e.get('selected_edge') is not None]
                avg_edge = sum(edges) / len(edges) if edges else 0
                
                all_runs.append({
                    'tournament_id': tournament_id,
                    'tournament_name': tournament_name,
                    'country': country,
                    'run_timestamp': run_timestamp,
                    'run_date': run_timestamp[:10] if run_timestamp else '',
                    'run_time': run_timestamp[11:19] if run_timestamp else '',
                    'total_events': total_events,
                    'winned_events': winned_events,
                    'lost_events': lost_events,
                    'pending_events': pending_events,
                    'win_rate': win_rate,
                    'avg_edge': avg_edge,
                    'model_stats': model_stats,
                    'last_trained': model_stats.get('last_trained', 'N/A'),
                    'test_accuracy': model_stats.get('test_accuracy', None),
                    'test_auc': model_stats.get('test_auc', None),
                    'n_future': model_stats.get('n_future', 0),
                    'n_detected_valued': model_stats.get('n_detected_valued', 0),
                    'n_historical': model_stats.get('n_historical', None),
                    'features_original': model_stats.get('features_original', None),
                    'features_final': model_stats.get('features_final', None),
                })
        
        all_runs.sort(key=lambda x: x['run_timestamp'], reverse=True)
        return all_runs
    
    def get_tournament_stats(self) -> Dict[str, Any]:
        stats = {}
        tournaments = self.get_tournaments()
        
        for tournament_id, tournament_data in tournaments.items():
            tournament_name = tournament_data.get("name", "unknown")
            country = tournament_data.get("country", "unknown")
            
            total_events = 0
            total_winned = 0
            total_lost = 0
            total_pending = 0
            total_edges = []
            runs_info = []
            
            for run_timestamp, run_data in tournament_data.get("prediction_runs", {}).items():
                events = run_data.get("event_bet", {})
                total_events += len(events)
                
                for event in events.values():
                    if event.get('winned') is True:
                        total_winned += 1
                    elif event.get('winned') is False:
                        total_lost += 1
                    else:
                        total_pending += 1
                    
                    if event.get("selected_edge"):
                        total_edges.append(event.get("selected_edge"))
                
                runs_info.append({
                    "timestamp": run_timestamp,
                    "n_events": len(events),
                    "model_stats": run_data.get("model_stats", {})
                })
            
            decided_events = total_winned + total_lost
            win_rate = total_winned / decided_events if decided_events > 0 else 0
            
            stats[tournament_id] = {
                "name": tournament_name,
                "country": country,
                "total_events": total_events,
                "total_winned": total_winned,
                "total_lost": total_lost,
                "total_pending": total_pending,
                "win_rate": win_rate,
                "avg_edge": sum(total_edges) / len(total_edges) if total_edges else 0,
                "runs": runs_info
            }
        
        return stats
    
    def get_date_range(self) -> tuple:
        events = self.get_all_events()
        dates = []
        
        for event in events:
            if event.get("datetime_obj"):
                dates.append(event["datetime_obj"].date())
        
        if dates:
            return min(dates), max(dates)
        return None, None

    def get_available_run_dates(self) -> List[str]:
        dates = set()
        tournaments = self.get_tournaments()
        
        for tournament_data in tournaments.values():
            for run_timestamp in tournament_data.get("prediction_runs", {}).keys():
                if run_timestamp:
                    date = run_timestamp[:10]
                    dates.add(date)
        
        return sorted(dates, reverse=True)

    def get_runs_by_date(self, date_filter: str = None) -> List[Dict[str, Any]]:
        all_runs = self.get_all_runs()
        if date_filter:
            return [r for r in all_runs if r['run_date'] == date_filter]
        return all_runs

# Instancia global
data_loader = DataLoader()
