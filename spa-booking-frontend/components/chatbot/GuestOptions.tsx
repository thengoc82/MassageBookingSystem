import CollapsibleSection from './CollapsibleSection';

type Props = {
  onSelect: (guests: number) => void;
  selectedGuests: number | null;
  isCompleted: boolean;
  onEdit: () => void;
};

export default function GuestOptions({ onSelect, selectedGuests, isCompleted, onEdit }: Props) {
  if (isCompleted && selectedGuests) {
    return (
      <CollapsibleSection
        title="Guests"
        isCompleted={isCompleted}
        summary={`${selectedGuests} ${selectedGuests > 1 ? 'people' : 'person'}`}
        onEdit={onEdit}
      >
        <></>
      </CollapsibleSection>
    );
  }

  return (
    <div className="flex gap-2">
      {[1, 2, 3].map((n) => (
        <button
          key={n}
          onClick={() => onSelect(n)}
          className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${
            selectedGuests === n
              ? "bg-indigo-600 text-white"
              : "bg-gray-200 hover:bg-gray-300"
          }`}
        >
          {n}
        </button>
      ))}
    </div>
  );
}
