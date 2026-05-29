import sqlite3

def get_player_stats(cursor, name):
    # Search by last name or full name
    cursor.execute('''
        SELECT player_id, first_name, last_name, team, position,
               goals, assists, points, games_played, toi_per_game,
               xGF_pct, CF_pct, PDO, rel_CF_pct, P60
        FROM players
        WHERE last_name LIKE ? OR (first_name || " " || last_name) LIKE ?
        LIMIT 1
    ''', (f'%{name}%', f'%{name}%'))
    return cursor.fetchone()

def get_all_stats(cursor, position):
    # Get all players at same position for percentile calculation
    # Group positions — F covers C/L/R, D covers D
    if position in ['C', 'L', 'R', 'LW', 'RW']:
        pos_filter = "position IN ('C', 'L', 'R', 'LW', 'RW', 'F')"
    else:
        pos_filter = "position = 'D'"

    cursor.execute(f'''
        SELECT xGF_pct, CF_pct, PDO, rel_CF_pct, P60
        FROM players
        WHERE {pos_filter}
        AND xGF_pct > 0
    ''')
    return cursor.fetchall()

def calculate_percentile(value, all_values, stat_index):
    vals = [row[stat_index] for row in all_values if row[stat_index] and row[stat_index] > 0]
    if not vals or not value:
        return 50
    below = sum(1 for v in vals if v < value)
    return round(below / len(vals) * 100)

def score_trade(p1_pcts, p2_pcts, metric_names):
    # p1 is what team A gives up
    # p2 is what team A receives
    # positive score = team A wins that metric
    scores = {}
    for i, metric in enumerate(metric_names):
        diff = p2_pcts[i] - p1_pcts[i]
        scores[metric] = diff
    return scores

def verdict_label(total_score):
    if total_score >= 20:
        return "CLEAR WIN"
    elif total_score >= 8:
        return "SLIGHT WIN"
    elif total_score >= -8:
        return "EVEN"
    elif total_score >= -20:
        return "SLIGHT LOSS"
    else:
        return "CLEAR LOSS"

def verdict_color(label):
    colors = {
        "CLEAR WIN":   "🟢",
        "SLIGHT WIN":  "🟡",
        "EVEN":        "⚪",
        "SLIGHT LOSS": "🟠",
        "CLEAR LOSS":  "🔴"
    }
    return colors.get(label, "⚪")

def plain_english_reason(scores, p1_name, p2_name):
    # Find the biggest difference metric
    biggest = max(scores, key=lambda k: abs(scores[k]))
    val = scores[biggest]

    labels = {
        'Scoring Threat (xGF%)': ('chance quality', 'chance quality'),
        'Puck Control (CF%)':    ('possession',     'possession'),
        'Luck Factor (PDO)':     ('sustainability', 'sustainability'),
        'Player Impact (relCF%)':('individual impact', 'individual impact'),
        'Scoring Rate (P/60)':   ('scoring rate',   'scoring rate'),
    }

    metric_label = labels.get(biggest, (biggest, biggest))

    if val > 0:
        return f"{p2_name} brings meaningfully better {metric_label[0]} than {p1_name} — the primary driver of this verdict."
    else:
        return f"{p1_name} had better {metric_label[1]} than {p2_name} — the acquiring team is giving up more than they are getting in this area."

def run_verdict(player1_name, player2_name):
    conn   = sqlite3.connect('tradelens.db')
    cursor = conn.cursor()

    # Pull both players
    p1 = get_player_stats(cursor, player1_name)
    p2 = get_player_stats(cursor, player2_name)

    if not p1:
        print(f"Player not found: {player1_name}")
        conn.close()
        return

    if not p2:
        print(f"Player not found: {player2_name}")
        conn.close()
        return

    p1_id, p1_first, p1_last, p1_team, p1_pos, p1_g, p1_a, p1_pts, p1_gp, p1_toi, p1_xgf, p1_cf, p1_pdo, p1_relcf, p1_p60 = p1
    p2_id, p2_first, p2_last, p2_team, p2_pos, p2_g, p2_a, p2_pts, p2_gp, p2_toi, p2_xgf, p2_cf, p2_pdo, p2_relcf, p2_p60 = p2

    p1_name = f"{p1_first} {p1_last}"
    p2_name = f"{p2_first} {p2_last}"

    # Get all players at same position for percentile calc
    all_p1 = get_all_stats(cursor, p1_pos)
    all_p2 = get_all_stats(cursor, p2_pos)

    # Calculate percentiles for each metric
    metrics = [
        'Scoring Threat (xGF%)',
        'Puck Control (CF%)',
        'Luck Factor (PDO)',
        'Player Impact (relCF%)',
        'Scoring Rate (P/60)',
    ]

    p1_raw  = [p1_xgf, p1_cf, p1_pdo, p1_relcf, p1_p60]
    p2_raw  = [p2_xgf, p2_cf, p2_pdo, p2_relcf, p2_p60]

    p1_pcts = [calculate_percentile(p1_raw[i], all_p1, i) for i in range(len(metrics))]
    p2_pcts = [calculate_percentile(p2_raw[i], all_p2, i) for i in range(len(metrics))]

    # Score the trade from perspective of team acquiring p2
    scores  = score_trade(p1_pcts, p2_pcts, metrics)

    # Weight the total score
    weights = [0.30, 0.20, 0.15, 0.20, 0.15]
    total   = sum(scores[m] * weights[i] for i, m in enumerate(metrics))
    total   = round(total, 1)

    verdict = verdict_label(total)
    icon    = verdict_color(verdict)
    reason  = plain_english_reason(scores, p1_name, p2_name)

    conn.close()

    # ── Print the full verdict ────────────────────────────────────────────────
    print("\n" + "="*60)
    print(f"  TRADELENS TRADE VERDICT")
    print("="*60)
    print(f"\n  {p1_team} SENDS      {p1_name}")
    print(f"  {p2_team} SENDS      {p2_name}")
    print(f"\n  Season: {p1_pts}pts in {p1_gp}GP | TOI: {p1_toi}")
    print(f"  Season: {p2_pts}pts in {p2_gp}GP | TOI: {p2_toi}")

    print(f"\n{'─'*60}")
    print(f"  {'METRIC':<28} {'GIVES UP':>10}  {'RECEIVES':>10}")
    print(f"{'─'*60}")

    for i, metric in enumerate(metrics):
        p1_bar = "█" * (p1_pcts[i] // 10)
        p2_bar = "█" * (p2_pcts[i] // 10)
        diff   = scores[metric]
        arrow  = "▲" if diff > 0 else ("▼" if diff < 0 else "─")
        print(f"  {metric:<28} {p1_pcts[i]:>8}th  {p2_pcts[i]:>8}th  {arrow}")

    print(f"\n{'─'*60}")
    print(f"\n  VERDICT:  {icon} {verdict}  (score: {total:+.1f})")
    print(f"\n  {reason}")
    print("\n" + "="*60 + "\n")

# ── Run it ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("TradeLens Verdict Engine")
    print("Enter player names to evaluate a trade\n")

    p1 = input("Player being SENT (e.g. Rakell): ").strip()
    p2 = input("Player being RECEIVED (e.g. Byfield): ").strip()

    run_verdict(p1, p2)