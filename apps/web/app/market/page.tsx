"use client";
import { MarketFeed } from "@/components/market-feed";
import { PageHeader } from "@/components/ui";

export default function MarketPage() {
  return (
    <>
      <PageHeader
        eyebrow="Change intelligence"
        title="The market is moving."
        description="Price moves, new serving options and capability changes — ranked,
        sourced and stamped. Every signal links to its source; formatting-only
        changes are excluded."
      />
      <MarketFeed />
    </>
  );
}
