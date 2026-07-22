import datetime as dt, time
from typing import Dict, List, Optional
import requests
import pandas as pd

SEASON = 2026
BATTER_REGRESSION_PA = 170
PITCHER_REGRESSION_BF = 250
EXPECTED_PA_BY_SLOT = {1:4.60,2:4.50,3:4.40,4:4.30,5:4.20,6:4.10,7:4.00,8:3.90,9:3.80}
DEFAULT_EXPECTED_PA = 4.10
PLATOON_ADVANTAGE_MULT = 1.08
PLATOON_DISADVANTAGE_MULT = 0.92
PARK_HR_FACTORS = {
    109:{"L":1.03,"R":1.05},144:{"L":1.05,"R":1.06},110:{"L":0.90,"R":1.05},
    111:{"L":1.00,"R":1.04},112:{"L":1.00,"R":1.00},145:{"L":1.09,"R":1.09},
    113:{"L":1.20,"R":1.16},114:{"L":0.95,"R":0.95},115:{"L":1.24,"R":1.24},
    116:{"L":0.92,"R":0.92},117:{"L":1.08,"R":1.03},118:{"L":0.95,"R":0.95},
    108:{"L":1.02,"R":1.02},119:{"L":1.06,"R":1.06},146:{"L":0.90,"R":0.90},
    158:{"L":1.08,"R":1.08},142:{"L":1.00,"R":1.00},121:{"L":0.97,"R":0.97},
    147:{"L":1.20,"R":1.05},133:{"L":1.00,"R":1.00},143:{"L":1.11,"R":1.08},
    134:{"L":0.90,"R":0.92},135:{"L":0.94,"R":0.90},137:{"L":0.92,"R":0.85},
    136:{"L":0.92,"R":0.92},138:{"L":0.95,"R":0.95},139:{"L":1.00,"R":1.00},
    140:{"L":1.05,"R":1.05},141:{"L":1.04,"R":1.03},120:{"L":1.00,"R":1.00},
}
DEFAULT_PARK_FACTOR = {"L":1.00,"R":1.00}
MIN_PA_FOR_POOL = 1
BASE = "https://statsapi.mlb.com/api/v1"

def _get(path, params=None, retries=3):
    url=f"{BASE}/{path.lstrip('/')}"
    for a in range(retries):
        try:
            r=requests.get(url,params=params,timeout=20); r.raise_for_status(); return r.json()
        except Exception as e:
            if a==retries-1: print(f"[api] failed {url}: {e}"); return {}
            time.sleep(1.0+a)
    return {}

def _num(x):
    try: return float(x)
    except (TypeError,ValueError): return 0.0

def get_games(date_str):
    data=_get("schedule",params={"sportId":1,"date":date_str,
              "hydrate":"probablePitcher,team,venue,lineups"})
    games=[]
    for db in data.get("dates",[]):
        for g in db.get("games",[]):
            venue=g.get("venue",{}) or {}; teams=g.get("teams",{}) or {}; lu=g.get("lineups",{}) or {}
            def side(kt,kl):
                t=teams.get(kt,{}) or {}; team=t.get("team",{}) or {}; sp=t.get("probablePitcher",{}) or {}
                lp=lu.get(kl,[]) or []
                return {"team_id":team.get("id"),"team_name":team.get("name","?"),
                        "sp_id":sp.get("id"),"sp_name":sp.get("fullName"),
                        "lineup":[p.get("id") for p in lp if p.get("id")]}
            games.append({"venue_name":venue.get("name","?"),
                          "home":side("home","homePlayers"),"away":side("away","awayPlayers")})
    return games

def get_active_hitters(team_id):
    data=_get(f"teams/{team_id}/roster",params={"rosterType":"active"}); ids=[]
    for e in data.get("roster",[]):
        pos=(e.get("position",{}) or {}).get("abbreviation","")
        pid=(e.get("person",{}) or {}).get("id")
        if pid and pos!="P": ids.append(pid)
    return ids

def get_handedness(ids):
    res={}; sids=[str(p) for p in ids if p]
    for i in range(0,len(sids),100):
        data=_get("people",params={"personIds":",".join(sids[i:i+100])})
        for pr in data.get("people",[]):
            pid=pr.get("id")
            if pid is None: continue
            res[pid]={"bats":(pr.get("batSide",{}) or {}).get("code"),
                      "throws":(pr.get("pitchHand",{}) or {}).get("code")}
    return res

def get_season_hitting(season):
    data=_get("stats",params={"stats":"season","group":"hitting","season":season,
              "gameType":"R","sportId":1,"limit":4000}); out={}
    for blk in data.get("stats",[]):
        for sp in blk.get("splits",[]):
            p=sp.get("player",{}) or {}; st=sp.get("stat",{}) or {}; pid=p.get("id")
            if pid is None: continue
            out[int(pid)]={"name":p.get("fullName","?"),"hr":_num(st.get("homeRuns")),
                           "pa":_num(st.get("plateAppearances"))}
    return out

def get_season_pitching(season):
    data=_get("stats",params={"stats":"season","group":"pitching","season":season,
              "gameType":"R","sportId":1,"limit":4000}); out={}
    for blk in data.get("stats",[]):
        for sp in blk.get("splits",[]):
            p=sp.get("player",{}) or {}; st=sp.get("stat",{}) or {}; pid=p.get("id")
            if pid is None: continue
            out[int(pid)]={"name":p.get("fullName","?"),"hr":_num(st.get("homeRuns")),
                           "bf":_num(st.get("battersFaced"))}
    return out

def build_batter_rates(hitting):
    thr=sum(v["hr"] for v in hitting.values()); tpa=sum(v["pa"] for v in hitting.values())
    league=thr/max(tpa,1); k=BATTER_REGRESSION_PA; rates={}
    for pid,v in hitting.items():
        rates[pid]={"name":v["name"],"pa":v["pa"],"hr":v["hr"],
                    "hr_pa":(v["hr"]+league*k)/(v["pa"]+k)}
    return rates,league

def build_pitcher_rates(pitching):
    thr=sum(v["hr"] for v in pitching.values()); tbf=sum(v["bf"] for v in pitching.values())
    league=thr/max(tbf,1); k=PITCHER_REGRESSION_BF; rates={}
    for pid,v in pitching.items():
        rates[pid]={"name":v["name"],"hr_bf":(v["hr"]+league*k)/(v["bf"]+k)}
    return rates,league

def _odds(p): p=min(max(p,1e-6),1-1e-6); return p/(1-p)
def log5_matchup(b,p,l): o=_odds(b)*_odds(p)/_odds(l); return o/(1+o)
def platoon_mult(bats,throws):
    if bats=="S": return PLATOON_ADVANTAGE_MULT
    if not bats or not throws: return 1.0
    return PLATOON_DISADVANTAGE_MULT if bats==throws else PLATOON_ADVANTAGE_MULT
def park_mult(tid,bats):
    f=PARK_HR_FACTORS.get(tid,DEFAULT_PARK_FACTOR)
    if bats=="L": return f["L"]
    if bats=="R": return f["R"]
    return (f["L"]+f["R"])/2.0
def game_hr_probability(pp,epa): pp=min(max(pp,0.0),1.0); return 1-(1-pp)**epa
def fair_american_odds(p):
    if p<=0: return "n/a"
    if p>=1: return "-inf"
    d=1/p; return f"+{round((d-1)*100)}" if d>=2 else f"-{round(100/(d-1))}"

def collect_pool(games):
    recs=[]
    for g in games:
        vh=g["home"]["team_id"]
        for sk,ok in (("home","away"),("away","home")):
            side=g[sk]; opp=g[ok]; lineup=side["lineup"]
            if lineup:
                for slot,pid in enumerate(lineup[:9],start=1):
                    recs.append({"mlbam_id":pid,"slot":slot,"batting_team":side["team_name"],
                        "opp_sp_id":opp["sp_id"],"opp_sp_name":opp["sp_name"] or "TBD",
                        "venue_team_id":vh,"sp_tbd":opp["sp_id"] is None})
            else:
                for pid in get_active_hitters(side["team_id"]):
                    recs.append({"mlbam_id":pid,"slot":None,"batting_team":side["team_name"],
                        "opp_sp_id":opp["sp_id"],"opp_sp_name":opp["sp_name"] or "TBD",
                        "venue_team_id":vh,"sp_tbd":opp["sp_id"] is None})
    return recs

def run(date_str,season=SEASON,top_n=30):
    games=get_games(date_str)
    if not games: print(f"No games found for {date_str}."); return pd.DataFrame()
    posted=sum(1 for g in games if g["home"]["lineup"] or g["away"]["lineup"])
    print(f"{len(games)} games on {date_str}; {posted} game-sides have posted lineups.")
    print("Pulling season stats from MLB Stats API...")
    bat_rates,league_bat=build_batter_rates(get_season_hitting(season))
    pit_rates,league_pit=build_pitcher_rates(get_season_pitching(season))
    pool=collect_pool(games)
    hands=get_handedness(list({*[r["mlbam_id"] for r in pool],
                               *[r["opp_sp_id"] for r in pool if r["opp_sp_id"]]}))
    rows=[]; seen=set(); missing=0
    for rec in pool:
        m=rec["mlbam_id"]
        if m in seen: continue
        seen.add(m)
        b=bat_rates.get(m)
        if not b or b["pa"]<MIN_PA_FOR_POOL: missing+=1; continue
        bats=(hands.get(m) or {}).get("bats")
        pinfo=pit_rates.get(rec["opp_sp_id"]) if rec["opp_sp_id"] else None
        prate=pinfo["hr_bf"] if pinfo else league_pit
        throws=(hands.get(rec["opp_sp_id"]) or {}).get("throws")
        _px=park_mult(rec["venue_team_id"],bats); _plx=platoon_mult(bats,throws)
        pp=log5_matchup(b["hr_pa"],prate,league_bat)*_px*_plx
        epa=EXPECTED_PA_BY_SLOT.get(rec["slot"],DEFAULT_EXPECTED_PA)
        pg=game_hr_probability(pp,epa)
        rows.append({"mlbam_id":m,"player":b["name"],"team":rec["batting_team"],"opp_SP":rec["opp_sp_name"],
            "slot":rec["slot"] or "-","exp_PA":round(epa,2),"season_HR":int(b["hr"]),
            "season_PA":int(b["pa"]),"p_HR_%":round(pg*100,1),"fair_odds":fair_american_odds(pg),
            "bats":bats or "?","throws":throws or "?","base_pct":round(b["hr_pa"]*100,1),
            "park_x":round(_px,3),"platoon_x":round(_plx,3),
            "pitch_x":round(prate/max(league_pit,1e-9),2),"venue_team_id":rec["venue_team_id"],
            "flags":("SP_TBD " if rec["sp_tbd"] else "")+("no_lineup" if rec["slot"] is None else "")})
    if not rows: print("No rankable batters."); return pd.DataFrame()
    df=pd.DataFrame(rows).sort_values("p_HR_%",ascending=False).reset_index(drop=True)
    df.index+=1; df.index.name="rank"
    if missing: print(f"Skipped {missing} batters (no season stats yet / too few PA).")
    print(f"\nTop {min(top_n,len(df))} HR prop candidates for {date_str}:\n")
    _hide=["mlbam_id","bats","throws","base_pct","park_x","platoon_x","pitch_x","venue_team_id"]
    print(df.drop(columns=[c for c in _hide if c in df.columns]).head(top_n).to_string())
    return df

# ============================ ACCURACY TRACKING =============================
import os
LOG_PATH_DRIVE = "/content/drive/MyDrive/hr_model_log.csv"
LOG_PATH_LOCAL = "hr_model_log.csv"

def _log_path():
    try:
        from google.colab import drive
        if not os.path.exists("/content/drive"):
            drive.mount("/content/drive")
        return LOG_PATH_DRIVE
    except Exception:
        print("(Drive not available - logging to a session file that resets when Colab closes.)")
        return LOG_PATH_LOCAL

def log_board(df, date_str, top_n=10, path=None):
    """Append the top-N predictions for a date so we can grade them later."""
    if df is None or len(df)==0:
        print("Nothing to log."); return
    path = path or _log_path()
    sub = df.head(top_n)[["mlbam_id","player","team","p_HR_%"]].copy()
    sub.insert(0,"pred_date",date_str)
    existing = None
    if os.path.exists(path):
        try:
            existing = pd.read_csv(path)
            existing = existing[existing["pred_date"]!=date_str]  # replace same-day re-runs
        except Exception:
            existing = None
    out = pd.concat([existing,sub],ignore_index=True) if existing is not None else sub
    out.to_csv(path,index=False)
    print(f"Logged top {top_n} predictions for {date_str} -> {path}")

def _homered_on(date_str):
    """Set of MLBAM ids that hit >=1 HR in Final games on a date."""
    sched=_get("schedule",params={"sportId":1,"date":date_str})
    pks=[]
    for db in sched.get("dates",[]):
        for g in db.get("games",[]):
            if (g.get("status",{}) or {}).get("abstractGameState")=="Final":
                pks.append(g.get("gamePk"))
    homered=set()
    for pk in pks:
        box=_get(f"game/{pk}/boxscore")
        for side in ("home","away"):
            players=((box.get("teams",{}) or {}).get(side,{}) or {}).get("players",{}) or {}
            for _,pl in players.items():
                hrn=(((pl.get("stats",{}) or {}).get("batting",{}) or {}).get("homeRuns"))
                pid=(pl.get("person",{}) or {}).get("id")
                if pid is not None and _num(hrn)>=1:
                    homered.add(int(pid))
    return homered, len(pks)

def grade(date_str, path=None):
    """Grade a past date's logged predictions against who actually homered.
    Run this the day AFTER, once games are Final."""
    path = path or _log_path()
    if not os.path.exists(path):
        print("No log file yet - run some boards first."); return
    log=pd.read_csv(path); day=log[log["pred_date"]==date_str].copy()
    if len(day)==0:
        print(f"No predictions logged for {date_str}."); return
    homered,ngames=_homered_on(date_str)
    if ngames==0:
        print(f"No Final games for {date_str} yet - grade later."); return
    day["hit"]=day["mlbam_id"].apply(lambda x:int(int(x) in homered))
    n=len(day); hits=int(day["hit"].sum())
    p=day["p_HR_%"]/100.0
    brier=float(((p-day["hit"])**2).mean())
    print(f"\n{date_str}: {hits}/{n} predicted hitters homered ({hits/n*100:.0f}%).  Brier={brier:.3f}")
    print("(Lower Brier = better calibration. A player at 20% should homer ~1 in 5 nights.)\n")
    print(day[["player","team","p_HR_%","hit"]].to_string(index=False))
    return day

def grade_all(path=None):
    """Overall calibration across every logged date that has finished."""
    path = path or _log_path()
    if not os.path.exists(path):
        print("No log file yet."); return
    log=pd.read_csv(path); frames=[]
    for d in sorted(log["pred_date"].unique()):
        homered,ng=_homered_on(d)
        if ng==0: continue
        sub=log[log["pred_date"]==d].copy()
        sub["hit"]=sub["mlbam_id"].apply(lambda x:int(int(x) in homered))
        frames.append(sub)
    if not frames:
        print("No finished dates to grade yet."); return
    allp=pd.concat(frames,ignore_index=True)
    n=len(allp); hits=int(allp["hit"].sum()); p=allp["p_HR_%"]/100.0
    print(f"\nAcross {allp['pred_date'].nunique()} nights, {n} predictions:")
    print(f"  Top-list hit rate: {hits}/{n} = {hits/n*100:.1f}%")
    print(f"  Brier score: {float(((p-allp['hit'])**2).mean()):.3f}")
    # calibration table
    allp["bucket"]=pd.cut(allp["p_HR_%"],bins=[0,10,15,20,25,100],
                          labels=["<10%","10-15%","15-20%","20-25%","25%+"])
    tab=allp.groupby("bucket",observed=True)["hit"].agg(["mean","count"])
    tab["predicted"]=allp.groupby("bucket",observed=True)["p_HR_%"].mean()/100
    print("\nCalibration (predicted vs actual HR rate by bucket):")
    print(tab[["predicted","mean","count"]].rename(columns={"mean":"actual","count":"n"}).to_string())
    return allp

def grade_log(log_df):
    """Grade an uploaded prediction log (DataFrame) against real results.
    Returns (per_date_df, calibration_df, overall_dict). API-driven."""
    frames=[]
    for d in sorted(log_df["pred_date"].astype(str).unique()):
        homered,ng=_homered_on(d)
        if ng==0:
            continue
        sub=log_df[log_df["pred_date"].astype(str)==d].copy()
        sub["hit"]=sub["mlbam_id"].apply(lambda x:int(int(x) in homered))
        frames.append(sub)
    if not frames:
        return None,None,None
    allp=pd.concat(frames,ignore_index=True)
    n=len(allp); hits=int(allp["hit"].sum()); p=allp["p_HR_%"]/100.0
    overall={"nights":int(allp["pred_date"].nunique()),"n":n,"hits":hits,
             "hit_rate":round(hits/n*100,1),"brier":round(float(((p-allp["hit"])**2).mean()),3)}
    per_date=(allp.groupby("pred_date")
                  .agg(picks=("hit","size"),homered=("hit","sum"))
                  .reset_index())
    allp["bucket"]=pd.cut(allp["p_HR_%"],bins=[0,10,15,20,25,100],
                          labels=["<10%","10-15%","15-20%","20-25%","25%+"])
    calib=(allp.groupby("bucket",observed=True)
               .agg(predicted=("p_HR_%","mean"),actual=("hit","mean"),n=("hit","size"))
               .reset_index())
    calib["predicted"]=(calib["predicted"]/100).round(3)
    calib["actual"]=calib["actual"].round(3)
    return per_date,calib,overall
