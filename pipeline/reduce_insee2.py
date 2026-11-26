import pandas as pd, os

RAW = "/home/dietpi/frciv/data_raw"
ACT = f"{RAW}/activite_x/DS_RP_TD_ACTIVITE_PCSACTIVITY_COMP_2023_data.csv"
DIP = f"{RAW}/diplomes_x/DS_RP_DIPLOMES_PRINC_2023_data.csv"

cols = ["GEO", "GEO_OBJECT", "SEX", "AGE", "EMPSTA_ENQ", "PCS", "EMP_ACTIVITY", "TIME_PERIOD", "OBS_VALUE"]
keep_act = []
it = pd.read_csv(ACT, sep=";", quotechar='"', usecols=cols, chunksize=1_000_000,
                 dtype={"GEO": str, "GEO_OBJECT": str, "SEX": str, "AGE": str, "EMPSTA_ENQ": str,
                        "PCS": str, "EMP_ACTIVITY": str, "TIME_PERIOD": str}, low_memory=False)
for i, ch in enumerate(it):
    m = (ch["GEO_OBJECT"].isin(["COM", "AAV2020"]) & (ch["SEX"] == "_T")
         & (ch["AGE"] == "Y_GE15") & (ch["EMPSTA_ENQ"] == "1") & (ch["TIME_PERIOD"] == "2023"))
    keep_act.append(ch[m])
act = pd.concat(keep_act, ignore_index=True)
print("activity kept", len(act), act.TIME_PERIOD.unique())
act.to_csv(f"{RAW}/act_reduced.csv", index=False, sep=";")

keep_dip = []
it = pd.read_csv(DIP, sep=";", quotechar='"', chunksize=1_000_000,
                 dtype={"GEO": str, "GEO_OBJECT": str, "SEX": str, "AGE": str, "EDUC": str, "TIME_PERIOD": str}, low_memory=False)
for i, ch in enumerate(it):
    m = ch["GEO_OBJECT"].isin(["COM", "AAV2020"]) & (ch["SEX"] == "_T") & (ch["AGE"] == "Y_GE15") & (ch["TIME_PERIOD"] == "2023")
    keep_dip.append(ch[m])
dip = pd.concat(keep_dip, ignore_index=True)
print("diplomas kept", len(dip), dip.TIME_PERIOD.unique())
dip.to_csv(f"{RAW}/dip_reduced.csv", index=False, sep=";")
print("done")
