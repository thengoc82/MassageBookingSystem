"use client";

import CollapsibleSection from "./CollapsibleSection";
import { Shop } from "@/lib/shop";

type Props = {
  shops: Shop[];
  onSelect: (shop: Shop) => void;
  selectedShopId: number | null;
  isCompleted: boolean;
  onEdit: () => void;
};

export default function ShopOptions({
  shops,
  onSelect,
  selectedShopId,
  isCompleted,
  onEdit,
}: Props) {
    if (isCompleted) {
    const selectedShop = shops.find((s) => s.shopId === selectedShopId);
    return (
      <CollapsibleSection
        title="Shop"
        isCompleted={isCompleted}
        summary={selectedShop?.shopName}
        onEdit={onEdit}
      >
        <></>
      </CollapsibleSection>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2">
      {shops.map((shop) => (
        <button
          key={shop.shopId}
          onClick={() => onSelect(shop)}
          className={`p-3 rounded-lg text-center font-semibold transition-colors ${
            selectedShopId === shop.shopId
              ? "bg-indigo-600 text-white"
              : "bg-gray-200 hover:bg-gray-300"
          }`}
        >
          {shop.shopName}
        </button>
      ))}
    </div>
  );
}
