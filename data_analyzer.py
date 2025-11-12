# data_analyzer.py
import pandas as pd
from datetime import date
import matplotlib.pyplot as plt
import os
import logging

logger = logging.getLogger(__name__)

class DataAnalyzer:
    def __init__(self):
        pass

    def _to_dataframe(self, matches):
        if not matches:
            return pd.DataFrame()
        df = pd.DataFrame(matches)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.date
        return df

    def get_daily_stats(self, matches):
        df = self._to_dataframe(matches)
        if df.empty:
            return []
        grouped = df.groupby('player').agg(
            matches=('match_id','count'),
            wins=('win','sum'),
            goals=('goals','sum'),
            goals_against=('goals_against','sum')
        ).reset_index()
        grouped['winrate'] = (grouped['wins'] / grouped['matches']).fillna(0).round(3)
        return grouped.to_dict(orient='records')

    def generate_excel_report(self, matches, filepath=None):
        df = self._to_dataframe(matches)
        if filepath is None:
            filepath = os.path.join('data', f"report_{date.today().isoformat()}.xlsx")
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="matches")
            summary = self.get_daily_stats(matches)
            pd.DataFrame(summary).to_excel(writer, index=False, sheet_name="summary")
        logger.info(f"Excel report saved to {filepath}")
        return filepath

    def generate_weekly_report_with_charts(self, matches, out_dir="data/reports"):
        os.makedirs(out_dir, exist_ok=True)
        df = self._to_dataframe(matches)
        if df.empty:
            return {}
        df['date'] = pd.to_datetime(df['date'])
        week_start = df['date'].min().date()
        agg = df.groupby('player').agg(matches=('match_id','count'), goals=('goals','sum'), wins=('win','sum')).reset_index()
        fig_path = os.path.join(out_dir, f"weekly_goals_{week_start.isoformat()}.png")
        plt.figure(figsize=(8,4))
        agg_sorted = agg.sort_values('goals', ascending=False).head(10)
        plt.bar(agg_sorted['player'].astype(str), agg_sorted['goals'])
        plt.xlabel("Player")
        plt.ylabel("Goals")
        plt.title(f"Top Goals Week of {week_start.isoformat()}")
        plt.tight_layout()
        plt.savefig(fig_path)
        plt.close()
        logger.info("Weekly chart saved to %s", fig_path)
        return {"chart": fig_path, "summary": agg.to_dict(orient='records')}
