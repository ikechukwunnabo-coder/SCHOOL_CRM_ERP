import { useCallback, useState } from "react";

export function useForm<T extends Record<string, string>>(initial: T) {
  const [values, setValues] = useState<T>(initial);

  const setField = useCallback((key: keyof T, value: string) => {
    setValues((current) => ({ ...current, [key]: value }));
  }, []);

  const reset = useCallback(() => setValues(initial), [initial]);

  return { values, setValues, setField, reset };
}
