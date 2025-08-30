import { useState, useEffect } from 'react';
import { apiService } from '../services/api';

export const useApi = () => {
  const [loadingStates, setLoadingStates] = useState(new Map());
  const [errorStates, setErrorStates] = useState(new Map());

  // Update loading states when they change in the service
  useEffect(() => {
    const interval = setInterval(() => {
      const newLoadingStates = new Map();
      const newErrorStates = new Map();

      // Check for any loading states
      for (const [key, loading] of apiService.loadingStates) {
        newLoadingStates.set(key, loading);
      }

      // Check for any error states
      for (const [key, error] of apiService.errorStates) {
        newErrorStates.set(key, error);
      }

      setLoadingStates(newLoadingStates);
      setErrorStates(newErrorStates);
    }, 100);

    return () => clearInterval(interval);
  }, []);

  const get = async (url, config = {}, options = {}) => {
    return await apiService.get(url, config, options);
  };

  const post = async (url, data, config = {}, options = {}) => {
    return await apiService.post(url, data, config, options);
  };

  const put = async (url, data, config = {}, options = {}) => {
    return await apiService.put(url, data, config, options);
  };

  const del = async (url, config = {}, options = {}) => {
    return await apiService.delete(url, config, options);
  };

  const isLoading = (key) => {
    return loadingStates.get(key) || false;
  };

  const getError = (key) => {
    return errorStates.get(key);
  };

  const clearError = (key) => {
    apiService.clearError(key);
    setErrorStates(prev => {
      const newStates = new Map(prev);
      newStates.delete(key);
      return newStates;
    });
  };

  const clearCache = (keyPattern) => {
    apiService.clearCache(keyPattern);
  };

  return {
    get,
    post,
    put,
    del,
    isLoading,
    getError,
    clearError,
    clearCache
  };
};