//+------------------------------------------------------------------+
//|                                              ORB_Pivots_EA.mq5  |
//|   Opening Range Breakout + Daily Pivot Points.                  |
//|   Mirrors backtest/engine.py (ORBPivotParams) -- pivot filter    |
//|   and pivot stop/target are OFF by default (plain ATR-buffered   |
//|   ORB baseline), matching the staged validation approach.        |
//|   NOT VALIDATED IN THE STRATEGY TESTER -- proof-of-concept code, |
//|   review before any demo/live deployment.                        |
//+------------------------------------------------------------------+
#property copyright "trading-systems"
#property version   "1.00"
#property strict

input int    OR_WindowBars      = 3;     // bars of the chart timeframe (3 x M5 = 15 min)
input int    Anchor_Hour_UTC    = 8;     // ~London open
input double K_Buffer_ATR       = 0.10;  // breakout confirmation buffer, x ATR
input int    ATR_Period         = 14;
input double Stop_ATR_Mult      = 1.0;   // floor on stop distance, x ATR
input double Target_ATR_Mult    = 2.0;   // used when UsePivotStopTarget = false
input int    Day_Boundary_Hour  = 22;    // ~17:00 ET FX day rollover, UTC
input int    Max_Trades_Per_Day = 2;
input int    Cutoff_Hour_UTC    = 18;    // no new entries after this UTC hour
input double Risk_Pct           = 0.5;   // percent of equity risked per trade
input bool   UsePivotFilter     = false; // bias filter: only trade with pivot-implied direction
input bool   UsePivotStopTarget = false; // stop = tighter-of(OR side, opposing pivot); target = next pivot
input bool   UseVolumeFilter    = false; // trade only on abnormal opening volume (docs' top ORB enhancement)
input double VolumeMult         = 1.0;   // today's OR-window volume must be >= this x trailing average
input int    VolumeLookbackDays = 14;
input int    Slippage_Points    = 30;
input int    MagicNumber        = 20260904;

int atrHandle;
double orHigh = 0, orLow = 0;
long   orVolumeToday = 0;
datetime orDay = 0;
bool orWindowClosed = false;
int tradesToday = 0;
datetime tradesTodayDate = 0;

// Trailing OR-window volume history, keyed by day -- used to compute the
// abnormal-volume filter without look-ahead (today never contributes to
// its own trailing baseline).
long   orVolumeHistory[];
datetime orVolumeHistoryDay[];

double pivotP, pivotR1, pivotR2, pivotS1, pivotS2;
datetime pivotDay = 0;

int OnInit()
{
   atrHandle = iATR(_Symbol, PERIOD_CURRENT, ATR_Period);
   if(atrHandle == INVALID_HANDLE) { Print("Failed to create ATR handle"); return INIT_FAILED; }
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { IndicatorRelease(atrHandle); }

//--- Standard floor-trader pivots from the fully-closed PRIOR day (per
//--- Day_Boundary_Hour), matching common/indicators.py::standard_pivots.
void UpdatePivots()
{
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   datetime dayKey = TimeCurrent() - (dt.hour * 3600 + dt.min * 60 + dt.sec);
   if(dt.hour < Day_Boundary_Hour) dayKey -= 86400;
   if(dayKey == pivotDay) return;
   pivotDay = dayKey;

   // Prior day's H/L/C: use the daily timeframe shifted by 1, which is a
   // reasonable broker-side proxy for a custom rollover hour. For exact
   // Day_Boundary_Hour alignment, replace with a manual scan of the last
   // 24h of bars ending at the boundary -- left as a follow-up refinement.
   double priorHigh = iHigh(_Symbol, PERIOD_D1, 1);
   double priorLow  = iLow(_Symbol, PERIOD_D1, 1);
   double priorClose= iClose(_Symbol, PERIOD_D1, 1);

   pivotP  = (priorHigh + priorLow + priorClose) / 3.0;
   pivotR1 = 2 * pivotP - priorLow;
   pivotS1 = 2 * pivotP - priorHigh;
   pivotR2 = pivotP + (priorHigh - priorLow);
   pivotS2 = pivotP - (priorHigh - priorLow);
}

//--- Opening range: accumulate high/low during the anchor window, freeze
//--- once the window closes for the rest of the trading day.
void UpdateOpeningRange()
{
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   datetime today = TimeCurrent() - (dt.hour * 3600 + dt.min * 60 + dt.sec);
   if(today != orDay)
   {
      // Day just rolled: archive YESTERDAY's completed OR volume into the
      // trailing history BEFORE resetting -- today's own volume must never
      // be part of its own baseline (matches the shift(1) in
      // backtest/engine.py::prepare_signals).
      if(orDay != 0 && orWindowClosed) PushOrVolumeHistory(orDay, orVolumeToday);
      orDay = today;
      orHigh = 0; orLow = 0; orVolumeToday = 0; orWindowClosed = false;
   }

   if(dt.hour != Anchor_Hour_UTC) return; // only accumulate during the anchor hour's first N bars

   static datetime lastBar = 0;
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 1);
   if(barTime == lastBar) return;
   lastBar = barTime;

   int barsIntoWindow = (int)((TimeCurrent() - (today + Anchor_Hour_UTC * 3600)) / PeriodSeconds(PERIOD_CURRENT));
   if(barsIntoWindow >= OR_WindowBars) { orWindowClosed = true; return; }

   double h = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double l = iLow(_Symbol, PERIOD_CURRENT, 1);
   if(orHigh == 0 || h > orHigh) orHigh = h;
   if(orLow == 0 || l < orLow) orLow = l;
   orVolumeToday += iVolume(_Symbol, PERIOD_CURRENT, 1);
}

void PushOrVolumeHistory(datetime day, long vol)
{
   int n = ArraySize(orVolumeHistory);
   ArrayResize(orVolumeHistory, n + 1);
   ArrayResize(orVolumeHistoryDay, n + 1);
   orVolumeHistory[n] = vol;
   orVolumeHistoryDay[n] = day;
}

//--- Trailing average of the last VolumeLookbackDays PRIOR days' OR volume
//--- (today's own value is never in orVolumeHistory yet at call time).
double GetTrailingAvgVolume()
{
   int n = ArraySize(orVolumeHistory);
   if(n == 0) return 0;
   int count = MathMin(n, VolumeLookbackDays);
   long total = 0;
   for(int i = n - count; i < n; i++) total += orVolumeHistory[i];
   return (double)total / count;
}

bool HasOpenPosition()
{
   for(int i = 0; i < PositionsTotal(); i++)
      if(PositionGetSymbol(i) == _Symbol && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
         return true;
   return false;
}

double CalcLotSize(double stopDistance)
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskAmount = equity * (Risk_Pct / 100.0);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize <= 0 || tickValue <= 0 || stopDistance <= 0) return 0.0;
   double valuePerUnit = tickValue / tickSize;
   double lots = riskAmount / (stopDistance * valuePerUnit);
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lots = MathFloor(lots / step) * step;
   return MathMax(minLot, MathMin(maxLot, lots));
}

datetime lastBarTime = 0;
bool IsNewBar()
{
   datetime t = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(t != lastBarTime) { lastBarTime = t; return true; }
   return false;
}

void OnTick()
{
   if(!IsNewBar()) return;
   UpdatePivots();
   UpdateOpeningRange();
   if(HasOpenPosition()) return;
   if(!orWindowClosed) return;

   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   datetime today = TimeCurrent() - (dt.hour * 3600 + dt.min * 60 + dt.sec);
   if(today != tradesTodayDate) { tradesTodayDate = today; tradesToday = 0; }
   if(tradesToday >= Max_Trades_Per_Day) return;
   if(dt.hour < Anchor_Hour_UTC || dt.hour >= Cutoff_Hour_UTC) return;

   double atrVals[2];
   if(CopyBuffer(atrHandle, 0, 0, 2, atrVals) < 2) return;
   double atrNow = atrVals[1];
   if(atrNow <= 0 || orHigh == 0 || orLow == 0) return;

   double closeNow = iClose(_Symbol, PERIOD_CURRENT, 1);
   double longTrigger = orHigh + K_Buffer_ATR * atrNow;
   double shortTrigger = orLow - K_Buffer_ATR * atrNow;

   bool longSignal = closeNow > longTrigger;
   bool shortSignal = closeNow < shortTrigger;
   if(UsePivotFilter)
   {
      longSignal = longSignal && (closeNow > pivotP);
      shortSignal = shortSignal && (closeNow < pivotP);
   }
   if(UseVolumeFilter)
   {
      double trailingAvg = GetTrailingAvgVolume();
      bool volumeOk = trailingAvg > 0 && orVolumeToday >= VolumeMult * trailingAvg;
      longSignal = longSignal && volumeOk;
      shortSignal = shortSignal && volumeOk;
   }
   if(!longSignal && !shortSignal) return;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   MqlTradeRequest req; MqlTradeResult res;
   ZeroMemory(req); ZeroMemory(res);
   req.action = TRADE_ACTION_DEAL; req.symbol = _Symbol; req.deviation = Slippage_Points;
   req.magic = MagicNumber; req.type_filling = ORDER_FILLING_IOC;

   if(longSignal)
   {
      double stop, target;
      if(UsePivotStopTarget)
      {
         double candidate = MathMin(orLow, pivotS1);
         double dist = ask - candidate;
         stop = (dist >= Stop_ATR_Mult * atrNow) ? candidate : ask - Stop_ATR_Mult * atrNow;
         target = pivotR1;
      }
      else { stop = ask - Stop_ATR_Mult * atrNow; target = ask + Target_ATR_Mult * atrNow; }
      double lots = CalcLotSize(ask - stop);
      if(lots <= 0) return;
      req.type = ORDER_TYPE_BUY; req.price = ask; req.volume = lots; req.sl = stop; req.tp = target;
      if(OrderSend(req, res)) tradesToday++;
   }
   else if(shortSignal)
   {
      double stop, target;
      if(UsePivotStopTarget)
      {
         double candidate = MathMax(orHigh, pivotR1);
         double dist = candidate - bid;
         stop = (dist >= Stop_ATR_Mult * atrNow) ? candidate : bid + Stop_ATR_Mult * atrNow;
         target = pivotS1;
      }
      else { stop = bid + Stop_ATR_Mult * atrNow; target = bid - Target_ATR_Mult * atrNow; }
      double lots = CalcLotSize(stop - bid);
      if(lots <= 0) return;
      req.type = ORDER_TYPE_SELL; req.price = bid; req.volume = lots; req.sl = stop; req.tp = target;
      if(OrderSend(req, res)) tradesToday++;
   }
}
//+------------------------------------------------------------------+
