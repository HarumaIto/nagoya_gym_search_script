import time
import datetime
import pandas as pd
import io
import os  # 追加: フォルダ操作のため
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
OUTPUT_DIR = "output" # 出力先フォルダ名
# ============================================

def main():
    # 出力用ディレクトリが存在しない場合は作成
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.add_argument('--headless') 
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    all_results = [] 

    # 日付計算（ファイル名用）
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=SEARCH_DAYS - 1)
    
    # ファイル名の作成（開始日_終了日）
    file_name = f"{start_date}_{end_date}.csv"
    output_path = os.path.join(OUTPUT_DIR, file_name)

    print(f"検索を開始します... (全{SEARCH_DAYS}日分)")
    print(f"保存先: {output_path}")

    try:
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

                # --- 結果テーブルの解析 ---
                html_io = io.StringIO(driver.page_source)
                
                try:
                    dfs = pd.read_html(html_io)
                except ValueError:
                    print("    -> 空き情報なし")
                    continue

                count = 0
                for df in dfs:
                    if len(df.columns) < 2:
                        continue
                        
                    keys = df.iloc[:, 0].astype(str).tolist()
                    
                    if "施設" in keys:
                        # 2列目を値として辞書作成
                        record = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
                        record['検索日付'] = date_display
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
            final_df = pd.concat(all_results, ignore_index=True)
            
            # 列の並び替え（検索日付を先頭へ）
            cols = final_df.columns.tolist()
            if '検索日付' in cols:
                cols.insert(0, cols.pop(cols.index('検索日付')))
            final_df = final_df[cols]

            # 指定したディレクトリへ保存
            final_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"完了しました！")
            print(f"保存ファイル: {output_path}")
        else:
            print("\n検索期間中に該当するデータは見つかりませんでした。")

    except Exception as e:
        print(f"全体エラー: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()