import time
import datetime
import pandas as pd
import io # 追加: 文字列をファイルのように扱うため
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException

# ================= 設定エリア =================
TARGET_URL = "https://www.net.city.nagoya.jp/cgi-bin/sp/sps04001"
TARGET_SPORT_VALUE = "023"  # 023:バスケットボール, 015:サッカーなど
SEARCH_DAYS = 30
OUTPUT_FILE_NAME = f"空き状況_{datetime.date.today()}.csv"
# ============================================

def main():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') 
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    all_results = [] 

    print(f"検索を開始します... (全{SEARCH_DAYS}日分)")

    try:
        start_date = datetime.date.today()

        for i in range(SEARCH_DAYS):
            current_date = start_date + datetime.timedelta(days=i)
            month_str = str(current_date.month).zfill(2)
            day_str = str(current_date.day).zfill(2)
            date_display = current_date.strftime('%Y-%m-%d')
            
            print(f"[{i+1}/{SEARCH_DAYS}] {date_display} を検索中...")

            driver.get(TARGET_URL)
            time.sleep(1)

            try:
                # --- フォーム入力 ---
                Select(driver.find_element(By.XPATH, "//select[@name='syumoku']")).select_by_value(TARGET_SPORT_VALUE)

                try:
                    Select(driver.find_element(By.XPATH, "//select[@name='month']")).select_by_value(month_str)
                    Select(driver.find_element(By.XPATH, "//select[@name='day']")).select_by_value(day_str)
                except NoSuchElementException:
                    print(f"    -> 日付選択不可: {date_display}")
                    continue

                Select(driver.find_element(By.XPATH, "//select[@name='kyoyo1']")).select_by_value("07")
                Select(driver.find_element(By.XPATH, "//select[@name='chiiki']")).select_by_value("20")

                driver.find_element(By.XPATH, "//input[@type='submit' and @value='照会']").click()
                time.sleep(2)

                # --- 結果テーブルの解析 (HTML解析ロジック修正) ---
                # HTMLソースをStringIOでラップして警告を回避
                html_io = io.StringIO(driver.page_source)
                
                # ページ内のすべてのテーブルを取得
                try:
                    dfs = pd.read_html(html_io)
                except ValueError:
                    # テーブルが一つもない場合
                    print("    -> 空き情報なし")
                    continue

                count = 0
                for df in dfs:
                    # 提供されたHTMLでは、1件の結果が「項目名」と「値」の2列の表になっています。
                    # 例:
                    # 0     1
                    # 地域   中川区
                    # 施設   露橋ＳＣ競技場
                    
                    # データフレームを転置したり辞書化して判定
                    # まず、カラム数が2列以上あるか確認
                    if len(df.columns) < 2:
                        continue
                        
                    # 1列目を文字列リストとして取得
                    keys = df.iloc[:, 0].astype(str).tolist()
                    
                    # 「施設」というキーワードが含まれている表だけを抽出対象とする
                    if "施設" in keys:
                        # 2列目を値として取得し、辞書型(key: value)に変換して1行のデータにする
                        # 0列目をキー、1列目を値として辞書作成
                        record = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
                        
                        # 日付情報を追加
                        record['検索日付'] = date_display
                        
                        # 不要なキー（No.や予約ボタンの列など）があれば削除も可能ですが、
                        # そのままCSVにしても問題ありません。
                        
                        # 結果リストに追加（DataFrame化するため）
                        all_results.append(pd.DataFrame([record]))
                        count += 1
                
                if count > 0:
                    print(f"    -> {count} 件のデータを取得")
                else:
                    print("    -> 空き情報なし")

            except Exception as e:
                print(f"    -> 処理エラー: {e}")

        # --- CSV書き出し ---
        if all_results:
            print("\n全データを結合中...")
            # 全ての辞書(DataFrame)を結合
            final_df = pd.concat(all_results, ignore_index=True)
            
            # 列の順番を整理（見やすくするため）
            cols = final_df.columns.tolist()
            # 「検索日付」を先頭に持ってくる
            if '検索日付' in cols:
                cols.insert(0, cols.pop(cols.index('検索日付')))
            final_df = final_df[cols]

            final_df.to_csv(OUTPUT_FILE_NAME, index=False, encoding='utf-8-sig')
            print(f"完了しました！ファイル名: {OUTPUT_FILE_NAME}")
        else:
            print("\n検索期間中に該当するデータは見つかりませんでした。")

    except Exception as e:
        print(f"全体エラー: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()