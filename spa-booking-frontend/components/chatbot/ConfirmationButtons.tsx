
type Props = {
  onConfirm: () => void;
  onCancel: () => void;
  disabled: boolean;
};

export default function ConfirmationButtons({
  onConfirm,
  onCancel,
  disabled,
}: Props) {
  return (
    <div className="flex justify-end space-x-2 p-2">
      <button
        onClick={onCancel}
        disabled={disabled}
        className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Cancel
      </button>
      <button
        onClick={onConfirm}
        disabled={disabled}
        className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Confirm
      </button>
    </div>
  );
}
