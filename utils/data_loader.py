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
            script_dir = Path(__file__).resolve().parent
            app_dir = script_dir.parent
            candidates = [
                app_dir / "bet_leagues.json"
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
            tournament_profit = 0.0
            
            for run_timestamp, run_data in tournament_data.get("prediction_runs", {}).items():
                events = run_data.get("event_bet", {})
                total_events += len(events)
                
                for event in events.values():
                    odds = float(event.get("selected_odds") or event.get("odds") or event.get("odd") or 1.0)
                    
                    if event.get('winned') is True:
                        total_winned += 1
                        tournament_profit += (odds - 1.0)
                    elif event.get('winned') is False:
                        total_lost += 1
                        tournament_profit -= 1.0
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
            win_rate = total_winned / decided_events if decided_events > 0 else 0.0
            roi = (tournament_profit / decided_events * 100.0) if decided_events > 0 else 0.0
            
            stats[tournament_id] = {
                "name": tournament_name,
                "country": country,
                "total_events": total_events,
                "total_winned": total_winned,
                "total_lost": total_lost,
                "total_pending": total_pending,
                "win_rate": win_rate,
                "profit": round(tournament_profit, 2),
                "roi": round(roi, 2),
                "avg_edge": sum(total_edges) / len(total_edges) if total_edges else 0.0,
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

    def get_analytics_summary(self) -> Dict[str, Any]:
        """
        Calcula métricas avanzadas de rendimiento cuantitativo:
        Profit (Unidades), ROI (Yield %), Curva temporal y Desglose por Cuotas.
        """
        events = self.get_all_events()
        
        decided_events = [e for e in events if e.get("winned") in (True, False)]
        
        total_events = len(events)
        decided_count = len(decided_events)
        total_winned = sum(1 for e in decided_events if e.get("winned") is True)
        total_lost = sum(1 for e in decided_events if e.get("winned") is False)
        total_pending = total_events - decided_count
        
        win_rate = total_winned / decided_count if decided_count > 0 else 0.0
        
        # Asumiendo Stake plano de 1 Unidad por apuesta
        total_staked = float(decided_count)
        total_profit = 0.0
        
        edges = []
        daily_stats = {}
        odds_brackets = {
            "< 1.50": {"total": 0, "winned": 0, "profit": 0.0},
            "1.50 - 1.80": {"total": 0, "winned": 0, "profit": 0.0},
            "1.80 - 2.20": {"total": 0, "winned": 0, "profit": 0.0},
            "> 2.20": {"total": 0, "winned": 0, "profit": 0.0},
        }
        bet_type_stats = {}

        # Ordenar eventos cronológicamente
        sorted_decided = sorted(
            decided_events, 
            key=lambda x: x.get("date_str") or "0000-00-00"
        )
        
        cumulative_units = 0.0

        for e in sorted_decided:
            odds = float(e.get("selected_odds") or e.get("odds") or e.get("odd") or 1.0)
            edge = float(e.get("selected_edge") or 0.0)
            edges.append(edge)
            
            is_win = e.get("winned") is True
            profit_unit = (odds - 1.0) if is_win else -1.0
            total_profit += profit_unit
            cumulative_units += profit_unit
            
            date_str = e.get("date_str") or "Desconocido"
            if date_str not in daily_stats:
                daily_stats[date_str] = {
                    "profit": 0.0,
                    "cumulative": 0.0,
                    "events": 0,
                    "winned": 0
                }
            daily_stats[date_str]["profit"] += profit_unit
            daily_stats[date_str]["events"] += 1
            if is_win:
                daily_stats[date_str]["winned"] += 1
            daily_stats[date_str]["cumulative"] = round(cumulative_units, 2)

            # Agrupación por Rangos de Cuotas
            if odds < 1.50:
                b_key = "< 1.50"
            elif odds <= 1.80:
                b_key = "1.50 - 1.80"
            elif odds <= 2.20:
                b_key = "1.80 - 2.20"
            else:
                b_key = "> 2.20"
                
            odds_brackets[b_key]["total"] += 1
            if is_win:
                odds_brackets[b_key]["winned"] += 1
            odds_brackets[b_key]["profit"] += profit_unit

            # Agrupación por Tipo de Apuesta / Mercado
            b_type = e.get("bet_type") or e.get("market") or e.get("selected_market") or "Principal"
            if b_type not in bet_type_stats:
                bet_type_stats[b_type] = {"total": 0, "winned": 0, "profit": 0.0}
            bet_type_stats[b_type]["total"] += 1
            if is_win:
                bet_type_stats[b_type]["winned"] += 1
            bet_type_stats[b_type]["profit"] += profit_unit

        roi = (total_profit / total_staked * 100.0) if total_staked > 0 else 0.0
        avg_edge = (sum(edges) / len(edges)) if edges else 0.0

        # Formatear torneos con Unidades y ROI
        tournament_stats = self.get_tournament_stats()
        for t_id, t_data in tournament_stats.items():
            t_decided = t_data.get("total_winned", 0) + t_data.get("total_lost", 0)
            t_profit = 0.0
            # Calcular profit específico del torneo
            for e in sorted_decided:
                if e.get("tournament_id") == t_id:
                    o = float(e.get("selected_odds") or e.get("odds") or 1.0)
                    t_profit += (o - 1.0) if e.get("winned") else -1.0
            
            t_data["profit"] = round(t_profit, 2)
            t_data["roi"] = round((t_profit / t_decided * 100.0), 2) if t_decided > 0 else 0.0

        return {
            "total_events": total_events,
            "decided_events": decided_count,
            "total_winned": total_winned,
            "total_lost": total_lost,
            "total_pending": total_pending,
            "win_rate": win_rate,
            "avg_edge": avg_edge,
            "total_profit": round(total_profit, 2),
            "roi": round(roi, 2),
            "daily_stats": daily_stats,
            "odds_brackets": odds_brackets,
            "bet_type_stats": bet_type_stats,
            "tournament_stats": tournament_stats
        }

# Instancia global
data_loader = DataLoader()
