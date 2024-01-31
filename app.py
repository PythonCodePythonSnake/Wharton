from json import loads, dump
from tvDatafeed import TvDatafeed, Interval
from datetime import timedelta, datetime
from flask import Flask, request, render_template, redirect
from yfinance import download
from pandas import DataFrame
app = Flask(__name__)

def update_data():
    global values
    tickers = list(values["Data"].keys())
    result = {}
    times = [(datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"), 
                datetime.today().strftime("%Y-%m-%d"), 
                (datetime.today() - timedelta(days=370)).strftime("%Y-%m-%d"), 
                (datetime.today() - timedelta(days=360)).strftime("%Y-%m-%d")]
    curr_data = download(" ".join(tickers), end=times[1], start=times[0])["Close"]
    prev_data = download(" ".join(tickers), end=times[3], start=times[2])["Close"]
    for ticker in tickers:
        if str(curr_data[ticker][-1]) == "nan" or str(prev_data[ticker][-1]) == "nan": continue
        try: result[ticker] = [round(curr_data[ticker][-1], 2), round(prev_data[ticker][-1], 2)]
        except: pass
    with open("values.json", "w") as file:
        dump({"Time": times[1], "Data":result}, file)
    with open("values.json") as file:
        values = dict(loads(file.read()))

@app.route("/")
def home():
    try: return render_template("Home.html")
    except: return redirect("/error")

@app.route("/fpp")
def index():
    try: return (render_template("fpp.html"))
    except: return redirect("/error")

@app.route("/fpp/search", methods=["POST"])
def stock_search():
    try:
        tv = TvDatafeed(username="", password="")
        global search
        stock = request.form["stock"]
        search = DataFrame(tv.search_symbol(stock))
        if search.empty: return redirect("/error")
        send_data, tickers = [], []
        for ind in search.index:
            if ind >= 30: break
            send_data.append([ind+1, search['exchange'][ind]+":"+search['symbol'][ind], search['type'][ind], search['description'][ind], search['country'][ind]])
            tickers.append(search['exchange'][ind]+":"+search['symbol'][ind])
        return (render_template("fpp-search.html", datatable=send_data, tickers=tickers))
    except: return redirect("/error")

@app.route("/fpp/details", methods=["POST"])
def get_details():
    try:
        def Volatality():
            global data
            net_vol, tot_val = 0, 0
            for i in range(len(data["close"])):
                net_vol += abs((data['high'][i] + data['low'][i]) - (data['close'][i] + data['open'][i]))
                tot_val += 1
            return (net_vol/tot_val)*100

        def Support_and_Resistance():
            global data
            return {"support" : min(data["low"]), "resistance": max(data["high"])}

        global search, data, curr_price, indicators
        ex, sym = request.form["ticker"].split(":")
        time_frame = request.form["time"]
        NUM_ROWS = 5000
        try: stock_data = tv.get_hist(sym, ex, Interval.in_3_minute, NUM_ROWS)
        except: return redirect("/error")
        stock_data = stock_data.iloc[::-1]
        
        if time_frame == "1": delta = timedelta(hours=-1)
        elif time_frame == "3": delta = timedelta(weeks=-1)
        elif time_frame == "4": delta = timedelta(days=-30)
        else: delta = timedelta(days=-1)
        top_time = datetime.strptime(str(stock_data.index[0]), '%Y-%m-%d %H:%M:%S')
        new_time = top_time + delta
        data = stock_data[stock_data.index > new_time]
        curr_price = data["close"][0]
        indicators["Vol"], indicators["SupRes"] = Volatality(), Support_and_Resistance()
        indicators["curr"] = curr_price
        return render_template("fpp-inputs.html", vol=f"{indicators['Vol']:.2f}")
    except: return redirect("/error")

@app.route("/peer")
def peer():
    try:
        global summ
        return (render_template("peer.html", sector_data=summ))
    except: return redirect("/error")

@app.route("/peer/result", methods=["POST"])
def peer_result():
    global sector_data, values
    all_tickers = sector_data[request.form["type"]][request.form["sector"]]
    result = []
    for ticker in all_tickers:
        curr = values["Data"][ticker]
        result.append([ticker, round((curr[0]-curr[1])/curr[1]*100, 2)])
    result = sorted(result, key=lambda x: x[1], reverse=True)
    return render_template("peer-result.html", datatable=result)

@app.route("/fpp/indicate", methods=["POST", "GET"])
def indicate():
    try: 
        def Position_and_Stop_Loss(position, stop_loss):
            if "$" in position: position = "".join(list(position)[1:])
            position = float(position)
            if "%" in stop_loss: stop_loss = "".join(list(stop_loss)[:-1])
            stop_loss = float(stop_loss)/100
            global curr_price
            low_limit = position * (1-stop_loss)
            if low_limit < curr_price:
                return -1, -1
            else: return position, stop_loss
        indicators["Pos"], indicators["Stop"] = Position_and_Stop_Loss(request.form["pos"], request.form["stop"])
        if indicators["curr"] < indicators["Pos"]*indicators["Stop"]: risk = 100
        else: risk = indicators['Vol']*(2 * indicators['curr'] - indicators['SupRes']['resistance'] - indicators['SupRes']['support'])
        if risk > 100: risk = 100
        elif risk < 0: risk = 0
        risk = round(risk, 2)
        return render_template("fpp-result.html", risk=risk)
    except: return redirect("/error")

@app.route("/error")
def error():
    return render_template("error.html")

@app.route("/contact")
def contact():
    try: return render_template("contact.html")
    except: return redirect("/error")
    
data = []
sector_data = {}
with open("ticker_classes.json") as file:
    sector_data = dict(loads(file.read()))
with open("values.json") as file:
    values = dict(loads(file.read()))
'''if values["Time"] != datetime.today().strftime("%Y-%m-%d"): 
    print("Updating Data")
    update_data()'''
summ = {}
summ["Stock"], summ["ETF"] = list(sector_data["Stock"].keys()), list(sector_data["ETF"].keys())
tv = TvDatafeed(username="", password="")
indicators = {}
