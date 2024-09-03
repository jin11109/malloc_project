import pandas as pd

TABLE_SIZE = 4096 * 16
PAGE_SIZE = 4096

def main():
    path = input("input cold mallocs table (should be total path) or 'enter' to skip\n")
    if len(path) == 0:
        cold_addrs_flag = [0] * TABLE_SIZE
        cold_addrs_page_flag = [0] * PAGE_SIZE
        with open("cold_addrs.h", 'w') as f:
            f.write(
                "#include<stdbool.h>\n" + \
                f"bool cold_addrs[{TABLE_SIZE}]" + " = {" + ", ".join(map(str, cold_addrs_flag)) + "};\n" + \
                f"bool cold_addrs_page[{PAGE_SIZE}]" + " = {" + ", ".join(map(str, cold_addrs_page_flag)) + "};\n"
            )
    else:
        df = pd.read_csv(path)

        df["page_index"] = df["alloc_addr_in_drcachesim"].apply(lambda x: int(x, 16) & (PAGE_SIZE - 1))

        cold_addrs_flag = [0] * TABLE_SIZE
        cold_addrs_page_flag = [0] * PAGE_SIZE
        for row in df.itertuples():
            if row.temperature != "cold":
                continue
            if pd.isna(row.real_machine):
                cold_addrs_page_flag[row.page_index] = 1
            else:
                cold_addrs_page_flag[row.page_index] = 0
                cold_addrs_flag[int(row.real_machine, 16) & (TABLE_SIZE - 1)] = 1

        with open("cold_addrs.h", 'w') as f:
            f.write(
                "#include<stdbool.h>\n" + \
                f"bool cold_addrs[{TABLE_SIZE}]" + " = {" + ", ".join(map(str, cold_addrs_flag)) + "};\n" + \
                f"bool cold_addrs_page[{PAGE_SIZE}]" + " = {" + ", ".join(map(str, cold_addrs_page_flag)) + "};\n"
            )
    
if __name__ == "__main__":
    main()
