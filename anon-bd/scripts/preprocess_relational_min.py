#!/usr/bin/env python3
import argparse, os, base64, hmac, hashlib, pandas as pd, yaml
from collections import defaultdict, deque

def b64url(x: bytes) -> str: return base64.urlsafe_b64encode(x).decode().rstrip("=")
def hmac_uid(salt, ns, val, L=16):
    v = "" if pd.isna(val) else str(val).strip().lower()
    msg = f"v1|{ns}|{v}".encode(); dig = hmac.new(salt.encode(), msg, hashlib.sha256).digest()
    return b64url(dig)[:L]

def topo(entities):
    g,ind=defaultdict(set),defaultdict(int)
    for n,c in entities.items():
        ind[n]+=0
        for fk,meta in (c.get("fks") or {}).items():
            r=meta.get("ref")
            if r and r!=n:
                if n not in g[r]: g[r].add(n); ind[n]+=1
    Q=[k for k,v in ind.items() if v==0]; out=[]
    while Q:
        u=Q.pop(0); out.append(u)
        for v in g[u]:
            ind[v]-=1
            if ind[v]==0: Q.append(v)
    if len(out)!=len(entities): raise SystemExit("Ciclo en FKs")
    return out

def main():
    ap=argparse.ArgumentParser(description="Relational pseudonymizer (compact)")
    ap.add_argument("--schema", required=True)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--maps-dir", default="maps")
    ap.add_argument("--pseudo-dir", default="pseudo")
    args=ap.parse_args()

    cfg=yaml.safe_load(open(args.schema,encoding="utf-8"))
    salts=cfg.get("salts") or {}; ents=cfg.get("entities") or {}
    os.makedirs(args.maps_dir, exist_ok=True); os.makedirs(args.pseudo_dir, exist_ok=True)

    # load dfs
    dfs={}
    for name,c in ents.items():
        path=os.path.join(args.input_dir, f"{c['table']}.csv")
        if not os.path.exists(path): raise SystemExit(f"Falta {path}")
        dfs[name]=pd.read_csv(path, dtype=str, encoding="utf-8")

    order=topo(ents); maps={}
    # build maps & add UIDs
    for name in order:
        c=ents[name]; df=dfs[name].copy()
        pk,canon,uid_name,uid_key=c.get("pk"),c.get("canonical"),c.get("uid_name"),c.get("uid_salt")
        if uid_name:
            if not uid_key or uid_key not in salts: raise SystemExit(f"[{name}] falta salt {uid_key}")
            base = df[canon] if canon and canon in df.columns else (df[pk] if pk in df.columns else None)
            if base is None: raise SystemExit(f"[{name}] no canonical ni pk")
            df[uid_name]=[hmac_uid(salts[uid_key], name, v) for v in base]
            keep=[uid_name]
            for col in [pk, canon]:
                if col and col in df.columns and col not in keep: keep.append(col)
            map_df=df[keep].drop_duplicates()
            maps[name]=map_df; map_df.to_csv(os.path.join(args.maps_dir,f"{name}_map.csv"), index=False)
        dfs[name]=df

    # replace FKs and drop columns -> pseudo
    for name in order:
        c=ents[name]; df=dfs[name].copy()
        for fk,meta in (c.get("fks") or {}).items():
            if fk not in df.columns: continue
            ref, out_col, ref_uid = meta.get("ref"), meta.get("out_col") or fk, meta.get("uid")
            if ref_uid is None: continue
            ref_map=maps.get(ref)
            if ref_map is None or ref_uid not in ref_map.columns:
                raise SystemExit(f"[{name}] falta mapa/ref_uid {ref}->{ref_uid}")
            ref_pk = ents[ref].get("pk")
            key = ref_pk if ref_pk and ref_pk in ref_map.columns else fk
            if key not in ref_map.columns: raise SystemExit(f"[{name}] no key {key} en mapa {ref}")
            df = df.merge(ref_map[[key, ref_uid]].drop_duplicates(), left_on=fk, right_on=key, how="left")
            df[out_col]=df[ref_uid]; df.drop(columns=[ref_uid, key], inplace=True, errors="ignore")
            if out_col!=fk: df.drop(columns=[fk], inplace=True, errors="ignore")
        drop = [d for d in (c.get("drop") or []) if d in df.columns]
        df.drop(columns=drop, inplace=True, errors="ignore")
        if c.get("pk") in df.columns and c.get("uid_name"): df.drop(columns=[c["pk"]], inplace=True, errors="ignore")
        uid=c.get("uid_name")
        if uid and uid in df.columns:
            cols=[uid]+[x for x in df.columns if x!=uid]; df=df[cols]
        df.to_csv(os.path.join(args.pseudo_dir,f"{name}_pseudo.csv"), index=False)

if __name__=="__main__":
    main()
