import { useState, useEffect, useRef } from 'react';

interface Props {
  isOpen: boolean;
  title?: string;
  placeholder?: string;
  onConfirm: (name: string) => void;
  onCancel: () => void;
}

export function SaveVersionModal({
  isOpen,
  title = 'Config verzió mentése',
  placeholder = 'pl. Baseline Q1, Optimizer v12...',
  onConfirm,
  onCancel,
}: Props) {
  const [name, setName] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setName('');
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const handleConfirm = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    onConfirm(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleConfirm();
    if (e.key === 'Escape') onCancel();
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.6)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}
    >
      <div className="bg-gray-800 border border-gray-600 rounded-xl p-6 w-full max-w-sm shadow-2xl">
        <h3 className="text-sm font-semibold text-gray-100 mb-1">{title}</h3>
        <p className="text-xs text-gray-400 mb-4">
          Adj nevet ennek a config verziónak, hogy később visszaállítható legyen.
        </p>
        <input
          ref={inputRef}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          maxLength={100}
          className="w-full bg-gray-700 border border-gray-500 rounded-lg px-3 py-2 text-sm
                     text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500
                     focus:ring-1 focus:ring-blue-500 mb-4"
        />
        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg text-xs text-gray-400 hover:text-gray-200
                       hover:bg-gray-700 transition-colors"
          >
            Mégse
          </button>
          <button
            onClick={handleConfirm}
            disabled={!name.trim()}
            className="px-4 py-2 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-500
                       text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Mentés
          </button>
        </div>
      </div>
    </div>
  );
}
