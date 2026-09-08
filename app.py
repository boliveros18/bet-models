# app.py 
from flask import Flask, render_template, request, jsonify
from flask_caching import Cache
import sys
import os
import re 
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.data_loader import data_loader
from utils.filters import filter_instance

app = Flask(__name__)
app.secret_key = 'tu-clave-secreta-aqui-cambiala-en-produccion'

cache = Cache(app, config={
    'CACHE_TYPE': 'filesystem',  
    'CACHE_DIR': 'cache',
    'CACHE_DEFAULT_TIMEOUT': 300
})

@app.template_filter('extract_teams')
def extract_teams(url):
    if not url:
        return "N/A"
    try:
        pattern = r'/football/([^/]+)/([^/]+)'
        match = re.search(pattern, url)
        if match:
            team1_raw = match.group(1) 
            team2_raw = match.group(2)  
            
            def clean_team(name):
                if '-' not in name:
                    return name
                parts = name.split('-')
                if len(parts) > 1:
                    team_name = '-'.join(parts[:-1])
                    return team_name.replace('-', ' ')
                return name
            
            team1 = clean_team(team1_raw)
            team2 = clean_team(team2_raw)
            
            return f"{team1} VS {team2}"
        else:
            return "No disponible"
    except Exception as e:
        return "Error"

@app.route('/')
def index():
    tournaments = data_loader.get_tournaments()
    stats = data_loader.get_tournament_stats()
    
    if not tournaments:
        return render_template('error.html', 
                             message="No se encontraron datos. Verifica que el archivo JSON existe.")
    
    total_events = sum(s['total_events'] for s in stats.values())
    total_winned = sum(s['total_winned'] for s in stats.values())
    total_lost = sum(s['total_lost'] for s in stats.values())
    total_decided = total_winned + total_lost
    total_win_rate = total_winned / total_decided if total_decided > 0 else 0
    
    min_date, max_date = data_loader.get_date_range()
    
    all_events = data_loader.get_all_events()
    
    now = datetime.now()
    
    future_events = [
        e for e in all_events 
        if e.get('winned') is None 
        and e.get('datetime_obj') is not None 
        and e['datetime_obj'] > now
    ]
    
    future_events = sorted(future_events, key=lambda x: x.get('country', '').lower())


    for event in future_events:
        event['teams'] = extract_teams(event.get('URL_m', ''))
    
    return render_template('index.html',
                         tournaments=tournaments,
                         stats=stats,
                         total_events=total_events,
                         total_winned=total_winned,
                         total_win_rate=total_win_rate,
                         min_date=min_date,
                         max_date=max_date,
                         pending_events=future_events)

@app.route('/tournaments')
def tournaments():
    tournaments = data_loader.get_tournaments()
    stats = data_loader.get_tournament_stats()
    return render_template('tournaments.html', 
                         tournaments=tournaments,
                         stats=stats)

@app.route('/events')
def events():
    date = request.args.get('date', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    tournament = request.args.get('tournament', '')
    country = request.args.get('country', '')
    winned = request.args.get('winned', '')
    min_edge = request.args.get('min_edge', type=float)
    max_edge = request.args.get('max_edge', type=float)
    bet_type = request.args.get('bet_type', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    events = filter_instance.apply_filters(
        date=date,
        start_date=start_date,
        end_date=end_date,
        tournament=tournament,
        country=country,
        winned=winned,
        min_edge=min_edge,
        max_edge=max_edge,
        bet_type=bet_type
    )
    
    events = sorted(events, key=lambda x: x.get('datetime', ''), reverse=True)
    
    total_events = len(events)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_events = events[start_idx:end_idx]
    
    tournaments_list = data_loader.get_tournaments()
    countries = sorted(set(e.get('country', '') for e in filter_instance.all_events if e.get('country')))
    bet_types = sorted(set(e.get('selected_bet', '') for e in filter_instance.all_events if e.get('selected_bet')))
    
    return render_template('events.html',
                         events=paginated_events,
                         total_events=total_events,
                         page=page,
                         per_page=per_page,
                         total_pages=max(1, (total_events + per_page - 1) // per_page),
                         tournaments=tournaments_list,
                         countries=countries,
                         bet_types=bet_types,
                         filters={
                             'date': date,
                             'start_date': start_date,
                             'end_date': end_date,
                             'tournament': tournament,
                             'country': country,
                             'winned': winned,
                             'min_edge': '' if min_edge is None else min_edge,
                             'max_edge': '' if max_edge is None else max_edge,
                             'bet_type': bet_type
                         })

@app.route('/stats')
def stats():
    stats_data = data_loader.get_tournament_stats()
    all_events = data_loader.get_all_events()
    
    total_events = len(all_events)
    total_winned = sum(1 for e in all_events if e.get('winned') is True)
    total_lost = sum(1 for e in all_events if e.get('winned') is False)
    total_pending = sum(1 for e in all_events if e.get('winned') is None)
    total_decided = total_winned + total_lost
    win_rate = total_winned / total_decided if total_decided > 0 else 0

    edges = [float(e.get('selected_edge', 0)) for e in all_events if e.get('selected_edge') is not None]
    avg_edge = sum(edges) / len(edges) if edges else 0

    total_profit = 0.0
    decided_events = [e for e in all_events if e.get('winned') in (True, False)]
    for e in decided_events:
        odds = float(e.get('selected_odds') or e.get('odds') or 1.0)
        total_profit += (odds - 1.0) if e.get('winned') is True else -1.0
        
    roi = (total_profit / total_decided * 100) if total_decided > 0 else 0.0

    bet_stats = {}
    for event in all_events:
        bet = event.get('selected_bet') or event.get('bet_type') or 'Desconocido'
        if bet not in bet_stats:
            bet_stats[bet] = {'total': 0, 'winned': 0, 'lost': 0, 'profit': 0.0}
        
        bet_stats[bet]['total'] += 1
        if event.get('winned') is True:
            bet_stats[bet]['winned'] += 1
            odds = float(event.get('selected_odds') or event.get('odds') or 1.0)
            bet_stats[bet]['profit'] += (odds - 1.0)
        elif event.get('winned') is False:
            bet_stats[bet]['lost'] += 1
            bet_stats[bet]['profit'] -= 1.0

    for bet, s in bet_stats.items():
        decided = s['winned'] + s['lost']
        s['win_rate'] = s['winned'] / decided if decided > 0 else 0.0
        s['roi'] = (s['profit'] / decided * 100) if decided > 0 else 0.0

    daily_stats = {}
    cumulative_profit = 0.0
    sorted_decided = sorted(decided_events, key=lambda x: x.get('date_str', '0000-00-00'))

    for event in sorted_decided:
        date_str = event.get('date_str', '')
        if date_str:
            if date_str not in daily_stats:
                daily_stats[date_str] = {'total': 0, 'winned': 0, 'lost': 0, 'profit': 0.0, 'cumulative': 0.0}
            
            daily_stats[date_str]['total'] += 1
            odds = float(event.get('selected_odds') or event.get('odds') or 1.0)
            is_win = event.get('winned') is True
            p = (odds - 1.0) if is_win else -1.0
            
            if is_win:
                daily_stats[date_str]['winned'] += 1
            else:
                daily_stats[date_str]['lost'] += 1
                
            daily_stats[date_str]['profit'] += p
            cumulative_profit += p
            daily_stats[date_str]['cumulative'] = round(cumulative_profit, 2)

    return render_template('stats.html',
                           total_events=total_events,
                           total_winned=total_winned,
                           total_lost=total_lost,
                           total_pending=total_pending,
                           win_rate=win_rate,
                           avg_edge=avg_edge,
                           total_profit=round(total_profit, 2),
                           roi=round(roi, 2),
                           bet_stats=bet_stats,
                           daily_stats=daily_stats,
                           tournament_stats=stats_data)

@app.route('/model-runs')
def model_runs():
    tournaments = data_loader.get_tournaments()
    all_runs = data_loader.get_all_runs()
    
    filter_date = request.args.get('date', '')
    
    if filter_date:
        display_runs = [r for r in all_runs if r['run_date'] == filter_date]
        title = f"| EJECUCIONES DEL {filter_date}"
    else:
        latest_runs = {}
        for run in all_runs:
            tournament_id = run['tournament_id']
            if tournament_id not in latest_runs or run['run_timestamp'] > latest_runs[tournament_id]['run_timestamp']:
                latest_runs[tournament_id] = run
        display_runs = list(latest_runs.values())
        display_runs.sort(key=lambda x: x['run_timestamp'], reverse=True)
        title = "| ULTIMAS EJECUCIONES POR LIGA"
    
    available_dates = data_loader.get_available_run_dates()
    
    total_runs = len(display_runs)
    total_events = sum(r['total_events'] for r in display_runs)
    total_winned = sum(r['winned_events'] for r in display_runs)
    total_pending = sum(r['pending_events'] for r in display_runs)
    total_lost = sum(r['lost_events'] for r in display_runs)
    total_decided = total_winned + total_lost
    overall_win_rate = total_winned / total_decided if total_decided > 0 else 0
    
    return render_template('model_runs.html',
                         all_runs=display_runs,
                         tournaments=tournaments,
                         available_dates=available_dates,
                         filter_date=filter_date,
                         title=title,
                         total_runs=total_runs,
                         total_events=total_events,
                         total_winned=total_winned,
                         total_pending=total_pending,
                         total_lost=total_lost,
                         overall_win_rate=overall_win_rate)

@app.route('/api/events')
def api_events():
    date = request.args.get('date', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    tournament = request.args.get('tournament', '')
    country = request.args.get('country', '')
    winned = request.args.get('winned', '')
    min_edge = request.args.get('min_edge', type=float)
    max_edge = request.args.get('max_edge', type=float)
    bet_type = request.args.get('bet_type', '')
    
    events = filter_instance.apply_filters(
        date=date,
        start_date=start_date,
        end_date=end_date,
        tournament=tournament,
        country=country,
        winned=winned,
        min_edge=min_edge,
        max_edge=max_edge,
        bet_type=bet_type
    )
    
    serializable_events = []
    for event in events:
        event_copy = {k: v for k, v in event.items() if k != 'datetime_obj'}
        if event.get('datetime_obj'):
            event_copy['datetime'] = event['datetime_obj'].isoformat()
        serializable_events.append(event_copy)

    return jsonify({
        'total': len(serializable_events),
        'events': serializable_events
    })

@app.route('/api/tournament/<tournament_id>')
def api_tournament(tournament_id):
    tournament = data_loader.get_tournament(tournament_id)
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404
    return jsonify(tournament)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Iniciando aplicación de análisis de apuestas")
    print("=" * 60)
    print(f"📁 Directorio actual: {os.getcwd()}")
    
    if not os.path.exists('cache'):
        os.makedirs('cache')
        print("📁 Carpeta cache creada")
    
    print("\n🌐 Servidor corriendo en: http://localhost:5000")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
