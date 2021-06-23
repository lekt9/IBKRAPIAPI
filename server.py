from flask import Flask, request
from flask_cors import CORS, cross_origin
from ib_insync import *
from ib_insync import contract as Contract
from ib_insync import IB, Index, Stock, OptionChain
from multiprocessing import Process
from tigeropen.common.util.contract_utils import option_contract
import random
from datetime import date, datetime, timedelta, timezone

# with IB() as ib:
ib = IB()
ib.connect('tws', 4001, clientId=random.randint(0, 9999))

app = Flask(__name__)
app.config['CORS_HEADERS'] = 'Content-Type'

CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/")
@cross_origin(origin='*')
def index():
    return "Welcome to lekt8's IBKR API API"

contractDetailsCache = {}
def getContractDetails(symbol):
    expired = []
    for key,value in contractDetailsCache.items():
        if value['timestamp'] < datetime.now()-timedelta(days=1):
            expired.append(key)
    for key in expired:
        contractDetailsCache.pop(key)
    if symbol not in contractDetailsCache:
        stock = Stock(symbol)
        details = ib.reqContractDetails(stock)
        contractDetailsCache[symbol] = {'timestamp': datetime.now(), 'details': details}

    return contractDetailsCache[symbol]['details']

optionsChainCache = {}
def getOptionsChain(symbol, details):
    expired = []
    for key,value in optionsChainCache.items():
        if value['timestamp'] < datetime.now()-timedelta(minutes=5):
            expired.append(key)
    for key in expired:
        optionsChainCache.pop(key)
    if symbol not in optionsChainCache:
        chain = ib.reqSecDefOptParams(symbol,'',underlyingSecType="STK", underlyingConId=details[0].contract.conId)
        optionsChainCache[symbol] = {'timestamp': datetime.now(), 'chain': chain}

    return optionsChainCache[symbol]['chain']

optionsBidAskCache = {}
def getOptionBidAsk(contract):
    contract = contract.replace(" ", "")

    expired = []
    for key,value in optionsBidAskCache.items():
        if value['timestamp'] < datetime.now()-timedelta(seconds=30):
            expired.append(key)
    for key in expired:
        optionsBidAskCache.pop(key)
    if contract not in optionsBidAskCache:
        optcontract = option_contract(contract)

        try:

            ibcontract = Contract.Option(optcontract.symbol,optcontract.expiry,optcontract.strike,optcontract.put_call[0].upper(),'SMART')
            # ib.reqMarketDataType(2)

            # tickdata = ib.reqTickByTickData(ibcontract,'BidAsk',1, False)
            # tickdata = ib.reqMktData(ibcontract ,"",True, False)

            tickdata = ib.reqHistoricalTicks(ibcontract, '', datetime.now(), 1, 'BID_ASK', useRth=False)[-1]

            # optionsBidAskCache[contract] = {'timestamp': datetime.now(), 'bidask': {'bid': tickdata.bid, 'ask': tickdata.ask}}
            optionsBidAskCache[contract] = {'timestamp': datetime.now(), 'bidask': {'bid': tickdata[2], 'ask': tickdata[3]}}

        except Exception as e:
            if 'list index out of range' in str(e):
                optionsBidAskCache[contract] = {'timestamp': datetime.now(), 'bidask': {'bid': 0, 'ask': 0}}
            else:
                raise e

    return optionsBidAskCache[contract]['bidask']

@app.route('/option/<contract>/', methods=['GET'])
@cross_origin(origin='*')
def getOptionPrice(contract):
    try:
        return getOptionBidAsk(contract),200
    except:
        return {'message': 'Error fetching contract price, check logs for details'},400

@app.route('/options/<symbol>/', methods=['GET'])
@cross_origin(origin='*')
def getOptionChain(symbol):

    try:
        details = getContractDetails(symbol)

        chain = getOptionsChain(symbol,details)

        expiries = chain[0].expirations
        strikes = chain[0].strikes

        return {
            "expirationDates": expiries,
            "strikes": strikes
        },200
    except Exception as e:
        print('error',e)
        return {'message': 'Error fetching options chain, check logs for details'},400

@app.route('/options/<symbol>/<expiry>', methods=['GET'])
@cross_origin(origin='*')
def getOptionChainStrikes(symbol,expiry):

    details = getContractDetails(symbol)

    chain = getOptionsChain(symbol,details)

    strikes = chain[0].strikes

    return {
        "strikes": strikes
    }   

@app.route('/options/<symbol>/<expiry>/<strike>', methods=['GET'])
@cross_origin(origin='*')
def getOptionPutCall(symbol,expiry,strike):
    
    chain = {}

    ibcontract = Contract.Option(symbol, expiry, strike, "CALL")
    chain["call"]=getOptionBidAsk(convertContractToString(ibcontract))
    ibcontract = Contract.Option(symbol, expiry, strike, "PUT")
    chain["put"]=getOptionBidAsk(convertContractToString(ibcontract))

    return {
        "chain": chain
    }

def convertContractToString(ibcontract):
    pc = ibcontract.right.upper()[:1]
    strike = '%09.3f' % float(ibcontract.strike)
    strike = str(strike).replace(".", "");

    return "{:<6}".format(ibcontract.symbol)+datetime.strptime(ibcontract.lastTradeDateOrContractMonth, '%Y%m%d').strftime('%y%m%d')+pc+strike