import pandas as pd

PAGE_SIZE = 4096

def main():
    path = input("input cold mallocs table (should be total path) or 'enter' to accept all\n")
    if len(path) == 0:
        cold_addrs_flag = [0] * PAGE_SIZE
        with open("cold_addrs.h", 'w') as f:
            f.write(
                "#include<stdbool.h>\n" + \
                f"bool cold_addrs[{PAGE_SIZE}]" + " = {" + ", ".join(map(str, cold_addrs_flag)) + "};"
            )
    else:
        df = pd.read_csv(path)

        df["page"] = df["alloc_addr_in_drcachesim"].apply(lambda x: int(x, 16) & (PAGE_SIZE - 1))

        cold_addrs_flag = [0] * PAGE_SIZE
        for page in df["page"]:
            cold_addrs_flag[page] = 1

        with open("cold_addrs.h", 'w') as f:
            f.write(
                "#include<stdbool.h>\n" + \
                f"bool cold_addrs[{PAGE_SIZE}]" + " = {" + ", ".join(map(str, cold_addrs_flag)) + "};"
            )
    
if __name__ == "__main__":
    main()
