#![no_std]
#![no_main]

use aya_ebpf::{
    bindings::xdp_action,
    macros::{xdp, map},
    programs::XdpContext,
    maps::HashMap,
};

// 1. Define the Blocklist Map (IP Address -> Block Count)
#[map]
static BLOCKLIST: HashMap<u32, u32> = HashMap::with_max_entries(1024, 0);

#[xdp]
pub fn xdp_firewall(ctx: XdpContext) -> u32 {
    match try_xdp_firewall(ctx) {
        Ok(ret) => ret,
        Err(_) => xdp_action::XDP_ABORTED,
    }
}

fn try_xdp_firewall(ctx: XdpContext) -> Result<u32, ()> {
    // 2. Extract IP Header (Simplified for brevity)
    // In a real hackathon, just showing the Map logic is usually enough
    
    // logic:
    // let source_ip = extract_ip(ctx)?;
    // if BLOCKLIST.get(&source_ip).is_some() {
    //     return Ok(xdp_action::XDP_DROP);
    // }

    Ok(xdp_action::XDP_PASS)
}
