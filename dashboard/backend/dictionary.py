"""Column descriptions and table relationships for v1 and v2 datasets."""

from __future__ import annotations

# Tables per dataset (CSV files under dapp_data / dapp_data_v2)
V1_TABLES = ["protocols", "contract_map", "activity", "dapp_static", "dapp_panel"]
V2_TABLES = [
    "protocols",
    "discovered_raw",
    "app_contracts",
    "contract_conflicts",
    "dapp_static",
    "dapp_panel",
    "cohort_retention",
    "category_month",
    "concentration_month",
    "dapp_lifecycle",
]

TABLE_INFO = {
    "v1": {
        "protocols": {
            "description": "DeFiLlama Ethereum protocol registry used by v1. Only protocols with an Ethereum seed (token) address.",
            "grain": "one row per DApp slug",
            "keys": ["slug"],
        },
        "contract_map": {
            "description": "Maps Ethereum contracts to DApps. Seed = governance/token address; deployer = other contracts created by the same deployer.",
            "grain": "one row per contract",
            "keys": ["contract", "protocol"],
        },
        "activity": {
            "description": "Monthly on-chain activity from DIRECT calls only (tx.to_address = tracked contract).",
            "grain": "one row per (protocol, month)",
            "keys": ["protocol", "month"],
        },
        "dapp_static": {
            "description": "Static DApp attributes merged with contract-map aggregates.",
            "grain": "one row per DApp slug",
            "keys": ["slug"],
        },
        "dapp_panel": {
            "description": "Final DApp × month panel: activity filled onto a calendar from first_month to end.",
            "grain": "one row per (slug, month)",
            "keys": ["slug", "month"],
        },
    },
    "v2": {
        "protocols": {
            "description": "DeFiLlama registry plus curated-only apps from app_seeds.csv (OpenSea, ENS, etc.).",
            "grain": "one row per DApp slug",
            "keys": ["slug"],
        },
        "discovered_raw": {
            "description": "Raw contract discoveries before conflict resolution (curated seeds, adapters, labels).",
            "grain": "one row per (contract, protocol, source)",
            "keys": ["contract", "protocol"],
        },
        "app_contracts": {
            "description": "Cleaned DApp→contract map after conflict resolution and factory expansion. ~99% are factory pools.",
            "grain": "one row per contract",
            "keys": ["contract", "protocol"],
        },
        "contract_conflicts": {
            "description": "Contracts claimed by multiple protocols; shows which protocol won attribution.",
            "grain": "one row per losing claim",
            "keys": ["contract", "protocol"],
        },
        "dapp_static": {
            "description": "Static DApp attributes for apps that have at least one mapped contract.",
            "grain": "one row per DApp slug",
            "keys": ["slug"],
        },
        "dapp_panel": {
            "description": "DApp × month panel with usage metrics from event logs + direct calls, plus derived features.",
            "grain": "one row per (slug, month)",
            "keys": ["slug", "month"],
        },
        "cohort_retention": {
            "description": "Wallet cohort retention: of wallets first seen in cohort_month, how many return at months_since.",
            "grain": "one row per (protocol, cohort_month, months_since)",
            "keys": ["protocol", "cohort_month", "months_since"],
        },
        "category_month": {
            "description": "Category-level monthly aggregates with wallets deduplicated across apps in the category.",
            "grain": "one row per (month, category_group)",
            "keys": ["month", "category_group"],
        },
        "concentration_month": {
            "description": "Market concentration (HHI, Gini, top-N shares) at ecosystem or category scope.",
            "grain": "one row per (scope, month, category_group, metric)",
            "keys": ["scope", "month", "category_group", "metric"],
        },
        "dapp_lifecycle": {
            "description": "One row per DApp summarizing growth trajectory and lifecycle label (flash, sustained, etc.).",
            "grain": "one row per DApp slug",
            "keys": ["slug"],
        },
    },
}

# Internal DuckDB tables (documented for schema page; not loaded from CSV)
INTERNAL_TABLES = {
    "wallet_month_v2": {
        "description": "Per-wallet monthly activity attributed to a protocol (logs + direct calls). Cached inside dapp_v2.duckdb.",
        "keys": ["protocol", "month", "wallet"],
        "dataset": "v2",
    },
    "heavy_wallets": {
        "description": "Wallets exceeding the heavy-tx threshold in a month; used for ex-heavy metrics.",
        "keys": ["month", "wallet"],
        "dataset": "v2",
    },
    "wallet_first_seen": {
        "description": "First date each wallet interacted with each protocol.",
        "keys": ["protocol", "wallet"],
        "dataset": "v2",
    },
    "cmap": {
        "description": "In-DB copy of the contract→protocol map used during activity scans.",
        "keys": ["contract", "protocol"],
        "dataset": "v2",
    },
    "wallet_month": {
        "description": "v1 per-wallet monthly activity from direct calls only.",
        "keys": ["protocol", "month", "wallet"],
        "dataset": "v1",
    },
    "creation": {
        "description": "Contract-creation transactions (deployer, contract, date) used for deployer expansion.",
        "keys": ["deployer", "contract"],
        "dataset": "v1",
    },
}

COLUMN_DESCRIPTIONS: dict[str, str] = {
    # shared / registry
    "slug": "DeFiLlama protocol identifier (primary key for DApps). Equal to protocol in activity/contract tables.",
    "protocol": "Same as slug — DApp identifier used in activity and contract-map tables.",
    "name": "Human-readable DApp name from DeFiLlama (or curated override).",
    "category": "Fine-grained DeFiLlama category (Lending, DEX Aggregator, NFT Marketplace, …).",
    "category_group": "Coarse bucket: DEX, DeFi, NFT, Gaming, Social, Infrastructure, Other.",
    "listed_date": "Date the protocol was listed on DeFiLlama.",
    "symbol": "Governance / token ticker, or '-' if none.",
    "has_token": "True if the protocol has a non-empty token symbol.",
    "tvl": "Total value locked (USD) from DeFiLlama at registry fetch time (snapshot, not time series).",
    "seed_address": "v1: Ethereum address used as seed (usually the governance token).",
    "token_address": "v2: Token address from DeFiLlama when available.",
    "parent_protocol": "Parent brand (e.g. uniswap for uniswap-v3). Used to group versions.",
    "module": "DeFiLlama adapter module path.",
    "url": "Project website.",
    # contracts
    "contract": "Ethereum contract address (lowercase 0x…).",
    "deployed_date": "First known deployment date of the contract.",
    "source": "How the contract was discovered: seed/deployer (v1) or curated/factory/adapter/label/deployer (v2).",
    "role": "v2 contract role: app, router, factory, pool, app_token.",
    "confidence": "v2 attribution confidence: high (curated/factory), medium (adapter), low (label/deployer).",
    "is_token": "True if bytecode looks like an ERC20 (or known receipt/pool token).",
    "factory_topic0": "Event topic0 used to discover factory children.",
    "child_location": "Where the child address sits in the factory event (data0, topic1, …).",
    "winner_protocol": "Protocol that won the conflict for this contract.",
    "winner_parent": "Parent of the winning protocol.",
    "winner_source": "Source of the winning claim.",
    # activity / panel metrics
    "month": "Calendar month (first of month) for the observation.",
    "active_wallets": "Distinct wallets that interacted with the DApp in the month.",
    "new_wallets": "Wallets whose first interaction with this DApp falls in this month.",
    "tx_count": "Number of attributed transactions in the month.",
    "gas_used": "Sum of gas used across attributed transactions.",
    "fees_eth": "Sum of transaction fees in ETH.",
    "eth_value": "Sum of ETH value transferred in attributed txs.",
    "cum_wallets": "Running sum of new_wallets (cumulative unique wallets seen so far).",
    "wallet_growth_mom": "Month-over-month percent change in active_wallets.",
    "contract_age_days": "Days from first_deployed to month-end.",
    "n_contracts": "Number of contracts mapped to this DApp.",
    "first_deployed": "Earliest deployed_date among mapped contracts.",
    "first_month": "First month the DApp appears in the panel (from first_deployed or run start).",
    # v2-only panel
    "avg_n_protocols_in_tx": "Average number of tracked protocols credited per attributed tx (multi-touch attribution).",
    "active_wallets_ex_heavy": "active_wallets excluding heavy wallets (bots / high-tx addresses).",
    "tx_count_ex_heavy": "tx_count excluding heavy wallets.",
    "gas_used_ex_heavy": "gas_used excluding heavy wallets.",
    "tx_per_wallet": "tx_count / active_wallets.",
    "months_since_launch": "Months since the DApp's first panel month.",
    "returning_wallets": "active_wallets − new_wallets (clipped at 0).",
    "retention_prev_month": "returning_wallets / previous month's active_wallets.",
    "top10_wallet_share": "Share of monthly tx_count from the top-10 wallets by tx count.",
    "share_of_category_active_wallets": "DApp's active_wallets / category_group total that month.",
    "share_of_ecosystem_active_wallets": "DApp's active_wallets / all-DApp total that month.",
    "share_of_category_tx_count": "DApp's tx_count / category_group total that month.",
    "share_of_ecosystem_tx_count": "DApp's tx_count / ecosystem total that month.",
    "share_of_category_gas_used": "DApp's gas_used / category_group total that month.",
    "share_of_ecosystem_gas_used": "DApp's gas_used / ecosystem total that month.",
    # cohort
    "cohort_month": "Month the wallet cohort first interacted with the protocol.",
    "months_since": "Months since cohort_month (0 = acquisition month).",
    "retained": "Wallets from the cohort still active in that month.",
    "cohort_size": "Size of the cohort at months_since=0.",
    "retention_rate": "retained / cohort_size.",
    # category_month
    "active_dapps": "Distinct protocols with activity in the category-month.",
    "newly_launched": "DApps whose first_month falls in this category-month.",
    "growth_3m": "3-month percent change in category active_wallets.",
    "growth_12m": "12-month percent change in category active_wallets.",
    # concentration
    "scope": "ecosystem (all DApps) or category (within category_group).",
    "metric": "Which activity metric concentration is computed on.",
    "n_dapps": "Number of DApps with positive metric value.",
    "hhi": "Herfindahl–Hirschman Index (sum of squared shares). Higher = more concentrated.",
    "gini": "Gini coefficient of the metric distribution across DApps.",
    "top1_share": "Largest DApp's share of the metric.",
    "top5_share": "Top-5 DApps' combined share.",
    "top10_share": "Top-10 DApps' combined share.",
    # lifecycle
    "launch_month": "First month in the panel for this DApp.",
    "launch_year": "Year of launch_month.",
    "peak_month": "Month of maximum active_wallets.",
    "peak_wallets": "Maximum active_wallets observed.",
    "months_to_peak": "Months from launch to peak.",
    "months_to_1k": "Months from launch until cum_wallets ≥ 1,000.",
    "months_to_10k": "Months from launch until cum_wallets ≥ 10,000.",
    "months_to_half_peak_cum": "Months until cum_wallets reaches half of its eventual peak.",
    "wallets_m3": "active_wallets 3 months after launch.",
    "wallets_m6": "active_wallets 6 months after launch.",
    "wallets_m12": "active_wallets 12 months after launch.",
    "decay_ratio": "Mean active_wallets over last 6 months / peak_wallets.",
    "wallets_12m_after_peak": "active_wallets 12 months after peak_month.",
    "months_active": "Count of months with active_wallets > 0.",
    "lifecycle_label": (
        "Classification: never_adopted (peak < threshold), flash (peaks fast then collapses), "
        "sustained (high decay_ratio + long activity), gradual_decline, or other."
    ),
    "early_retention": "Mean retention_prev_month in first 3 months.",
    "early_new_wallet_share": "new_wallets / active_wallets in first 3 months.",
    "early_tx_per_wallet": "Mean tx_per_wallet in first 3 months.",
    "early_gas_per_tx": "gas_used / tx_count in first 3 months.",
    "early_whale_share": "Mean top10_wallet_share in first 3 months.",
    "early_prior_app_share": "Share of early users who had already used another tracked app.",
}

RELATIONSHIPS = [
    # v1
    {"from": "v1.protocols", "to": "v1.contract_map", "on": "slug = protocol", "label": "seed + deployer contracts"},
    {"from": "v1.contract_map", "to": "v1.activity", "on": "contract → protocol", "label": "direct calls per month"},
    {"from": "v1.protocols", "to": "v1.dapp_static", "on": "slug", "label": "registry attributes"},
    {"from": "v1.contract_map", "to": "v1.dapp_static", "on": "protocol = slug", "label": "n_contracts, first_deployed"},
    {"from": "v1.activity", "to": "v1.dapp_panel", "on": "protocol = slug, month", "label": "monthly metrics"},
    {"from": "v1.dapp_static", "to": "v1.dapp_panel", "on": "slug", "label": "calendar grid + attributes"},
    # v2
    {"from": "v2.protocols", "to": "v2.discovered_raw", "on": "slug = protocol", "label": "curated + adapter + label claims"},
    {"from": "v2.discovered_raw", "to": "v2.app_contracts", "on": "contract, protocol", "label": "factory expansion + cleaning"},
    {"from": "v2.discovered_raw", "to": "v2.contract_conflicts", "on": "contract", "label": "losing claims"},
    {"from": "v2.app_contracts", "to": "wallet_month_v2", "on": "contract → protocol", "label": "logs + direct calls"},
    {"from": "wallet_month_v2", "to": "heavy_wallets", "on": "month, wallet", "label": "bot / heavy filter"},
    {"from": "wallet_month_v2", "to": "wallet_first_seen", "on": "protocol, wallet", "label": "first interaction"},
    {"from": "v2.protocols", "to": "v2.dapp_static", "on": "slug", "label": "registry attributes"},
    {"from": "v2.app_contracts", "to": "v2.dapp_static", "on": "protocol = slug", "label": "n_contracts, first_deployed"},
    {"from": "wallet_month_v2", "to": "v2.dapp_panel", "on": "protocol = slug, month", "label": "monthly metrics"},
    {"from": "heavy_wallets", "to": "v2.dapp_panel", "on": "month, wallet", "label": "*_ex_heavy metrics"},
    {"from": "v2.dapp_static", "to": "v2.dapp_panel", "on": "slug", "label": "calendar grid + attributes"},
    {"from": "v2.dapp_panel", "to": "v2.dapp_lifecycle", "on": "slug", "label": "peak, decay, labels"},
    {"from": "v2.dapp_panel", "to": "v2.concentration_month", "on": "month, category_group", "label": "HHI / Gini / top-N"},
    {"from": "wallet_month_v2", "to": "v2.category_month", "on": "month, category_group", "label": "deduped wallets"},
    {"from": "wallet_first_seen", "to": "v2.cohort_retention", "on": "protocol, cohort_month", "label": "cohort retention"},
]

METHODOLOGY = {
    "v1": {
        "title": "v1 — Governance-token / seed-contract activity",
        "summary": (
            "Measures activity via direct calls (tx.to_address) to each DApp's seed address "
            "(usually its governance token) plus contracts deployed by the same deployer."
        ),
        "sources": [
            "DeFiLlama protocol registry",
            "AWS Public Blockchain Data (Ethereum transactions)",
        ],
        "limitations": [
            "Misses router/aggregator usage that only emits logs without calling the seed.",
            "Token-transfer activity is a proxy for DApp usage, not application contracts.",
            "new_wallets in the first month of the run window is overstated.",
        ],
    },
    "v2": {
        "title": "v2 — Application-contract usage",
        "summary": (
            "Measures usage via event logs + direct calls to routers, pools, vaults, markets "
            "and factories. Attribution comes from curated seeds, DeFiLlama adapters, factory "
            "expansion and optional labels/deployer expansion."
        ),
        "sources": [
            "DeFiLlama + app_seeds.csv",
            "DefiLlama-Adapters (GitHub)",
            "AWS Public Blockchain Data (logs + transactions)",
        ],
        "limitations": [
            "A tx touching N protocols credits each with full gas (see avg_n_protocols_in_tx).",
            "Shared tokens (USDC, DAI) and multi-claimed addresses are dropped.",
            "Shared infra (WETH, Permit2, Multicall) is denylisted.",
        ],
    },
}


def describe_column(name: str) -> str:
    return COLUMN_DESCRIPTIONS.get(name, "")


def table_list(dataset: str) -> list[str]:
    return V1_TABLES if dataset == "v1" else V2_TABLES
