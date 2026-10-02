import { MODEL_PROVIDERS } from "../api/types";

type Props = {
  modelProvider: string;
  disabled: boolean;
  onChange: (modelProvider: string) => void;
};

export function ModelPicker({ modelProvider, disabled, onChange }: Props) {
  // A session can be running on a provider the picker does not offer — the
  // canned `echo` one, say — and showing that beats naming the wrong model.
  const options = MODEL_PROVIDERS.some((option) => option.value === modelProvider)
    ? [...MODEL_PROVIDERS]
    : [...MODEL_PROVIDERS, { value: modelProvider, label: modelProvider }];

  return (
    <div className="model-picker">
      <label htmlFor="model">Model</label>
      <select
        id="model"
        value={modelProvider}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {modelProvider === "anthropic" && (
        <p className="hint">Hosted, and quicker. Costs about a cent a question.</p>
      )}
    </div>
  );
}
