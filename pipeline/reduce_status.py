import pandas as pd

RAW = "/home/dietpi/frciv/data_raw"
ACT = f"{RAW}/activite_x/DS_RP_TD_ACTIVITE_PCSACTIVITY_COMP_2023_data.csv"
cols = ["GEO", "GEO_OBJECT", "SEX", "AGE", "EMPSTA_ENQ", "PCS", "EMP_ACTIVITY", "TIME_PERIOD", "OBS_VALUE"]
keep = []
it = pd.read_csv(ACT, sep=";", quotechar='"', usecols=cols, chunksize=1_000_000,
                 dtype={"GEO": str, "GEO_OBJECT": str, "SEX": str, "AGE": str, "EMPSTA_ENQ": str,
                        "PCS": str, "EMP_ACTIVITY": str, "TIME_PERIOD": str}, low_memory=False)
for ch in it:
    m = (ch["GEO_OBJECT"].isin(["COM", "AAV2020"]) & (ch["SEX"] == "_T") & (ch["AGE"] == "Y_GE15")
         & (ch["PCS"] == "_T") & (ch["EMP_ACTIVITY"] == "_T") & (ch["TIME_PERIOD"] == "2023")
         & (ch["EMPSTA_ENQ"].isin(["1", "2"])))
    keep.append(ch[m])
d = pd.concat(keep, ignore_index=True)
print("rows", len(d))
d.to_csv(f"{RAW}/act_status.csv", index=False, sep=";")
print("done")
