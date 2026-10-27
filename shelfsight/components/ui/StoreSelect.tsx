import { STORE_OPTIONS } from "@/lib/config";
import { UPLOADER_TEXT } from "@/lib/content";

interface StoreSelectProps {
  id: string;
  value: string;
  onChange: (storeId: string) => void;
  disabled?: boolean;
}

export function StoreSelect({ id, value, onChange, disabled = false }: StoreSelectProps) {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-sm font-medium">
        {UPLOADER_TEXT.storeLabel}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        className="h-11 w-full rounded-lg border border-zinc-300 bg-white px-3 text-sm dark:border-zinc-700 dark:bg-zinc-900"
      >
        {STORE_OPTIONS.map((store) => (
          <option key={store.id} value={store.id}>
            {store.name}
          </option>
        ))}
      </select>
    </div>
  );
}