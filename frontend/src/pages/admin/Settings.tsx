import React, { useState, useEffect } from 'react';
import { api } from '../../services/apiClient';
import { ServiceCategory, SLATier, MatchingConfig } from '../../types';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Tabs } from '../../components/common/Tabs';
import { Modal } from '../../components/common/Modal';
import { Skeleton } from '../../components/common/Skeleton';
import { useToast } from '../../components/common/Toast';
import { SettingsIcon, RefreshCwIcon } from '../../components/common/Icons';

export const Settings: React.FC = () => {
  const { success, error: toastError, warning } = useToast();

  const [activeTab, setActiveTab] = useState<'matching' | 'categories' | 'sla'>('matching');
  const [loading, setLoading] = useState(true);

  // Matching Weights & Timeouts State
  const [config, setConfig] = useState<MatchingConfig | null>(null);
  const [wDist, setWDist] = useState(0.35);
  const [wRating, setWRating] = useState(0.25);
  const [wWorkload, setWWorkload] = useState(0.2);
  const [wSkill, setWSkill] = useState(0.15);
  const [wAccept, setWAccept] = useState(0.05);
  const [offerTimeout, setOfferTimeout] = useState(120);
  const [highRiskTimeout, setHighRiskTimeout] = useState(60);
  const [maxAttempts, setMaxAttempts] = useState(5);
  const [savingConfig, setSavingConfig] = useState(false);

  // Categories State
  const [categories, setCategories] = useState<ServiceCategory[]>([]);
  const [catModalOpen, setCatModalOpen] = useState(false);
  const [catName, setCatName] = useState('');
  const [catDesc, setCatDesc] = useState('');
  const [catIcon, setCatIcon] = useState('🔧');
  const [catRate, setCatRate] = useState(2.5);
  const [catCert, setCatCert] = useState(2);
  const [savingCat, setSavingCat] = useState(false);

  // SLA Tiers State
  const [tiers, setTiers] = useState<SLATier[]>([]);
  const [tierModalOpen, setTierModalOpen] = useState(false);
  const [tierName, setTierName] = useState('');
  const [tierPriority, setTierPriority] = useState(3);
  const [tierResponse, setTierResponse] = useState(30);
  const [tierResolution, setTierResolution] = useState(120);
  const [savingTier, setSavingTier] = useState(false);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const [cfgData, catData, tierData] = await Promise.all([
        api.admin.getMatchingConfig(),
        api.admin.getCategories(),
        api.admin.getSLATiers(),
      ]);
      setConfig(cfgData);
      setWDist(cfgData.weight_distance);
      setWRating(cfgData.weight_rating);
      setWWorkload(cfgData.weight_workload);
      setWSkill(cfgData.weight_skill_level);
      setWAccept(cfgData.weight_acceptance_rate);
      setOfferTimeout(cfgData.offer_timeout_seconds);
      setHighRiskTimeout(cfgData.high_risk_offer_timeout_seconds);
      setMaxAttempts(cfgData.max_offer_attempts);

      setCategories(catData || []);
      setTiers(tierData || []);
    } catch (err: any) {
      toastError('Settings Error', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const totalWeight = Math.round((wDist + wRating + wWorkload + wSkill + wAccept) * 100);

  const handleSaveMatching = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingConfig(true);
    try {
      await api.admin.updateMatchingConfig({
        weight_distance: wDist,
        weight_rating: wRating,
        weight_workload: wWorkload,
        weight_skill_level: wSkill,
        weight_acceptance_rate: wAccept,
        offer_timeout_seconds: offerTimeout,
        high_risk_offer_timeout_seconds: highRiskTimeout,
        max_offer_attempts: maxAttempts,
      });
      success('Weights Saved', 'Dispatch matching engine recalibrated.');
    } catch (err: any) {
      toastError('Save failed', err.message);
    } finally {
      setSavingConfig(false);
    }
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!catName.trim()) return;
    setSavingCat(true);
    try {
      await api.admin.createCategory({
        name: catName,
        description: catDesc,
        icon: catIcon,
        price_per_minute: catRate,
        required_certification_level: catCert,
      });
      success('Category Created', `${catName} added to service catalog.`);
      setCatModalOpen(false);
      setCatName('');
      setCatDesc('');
      const updated = await api.admin.getCategories();
      setCategories(updated);
    } catch (err: any) {
      toastError('Creation failed', err.message);
    } finally {
      setSavingCat(false);
    }
  };

  const handleCreateTier = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tierName.trim()) return;
    setSavingTier(true);
    try {
      await api.admin.createSLATier({
        name: tierName,
        priority_level: tierPriority,
        response_time_minutes: tierResponse,
        resolution_time_minutes: tierResolution,
        is_default: false,
      });
      success('SLA Tier Created', `${tierName} tier saved.`);
      setTierModalOpen(false);
      setTierName('');
      const updated = await api.admin.getSLATiers();
      setTiers(updated);
    } catch (err: any) {
      toastError('Creation failed', err.message);
    } finally {
      setSavingTier(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text">Engine Rules & Configuration</h1>
        <p className="text-xs text-text-muted mt-0.5">
          Tune matching algorithm weights, customize SLA tiers, and manage service categories
        </p>
      </div>

      <Tabs
        tabs={[
          { id: 'matching', label: 'Matching Weights & Timeouts' },
          { id: 'categories', label: 'Service Categories', count: categories.length },
          { id: 'sla', label: 'SLA Tiers & Deadlines', count: tiers.length },
        ]}
        activeTab={activeTab}
        onChange={(id) => setActiveTab(id as any)}
      />

      {loading ? (
        <Skeleton height="300px" />
      ) : activeTab === 'matching' ? (
        <form onSubmit={handleSaveMatching} className="space-y-6">
          <Card padding="lg" className="space-y-5 border-border">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div>
                <h3 className="text-sm font-bold text-text">Technician Scoring Weights</h3>
                <p className="text-[11px] text-text-muted mt-0.5">
                  Relative weight assigned to candidate ranking factors
                </p>
              </div>
              <span
                className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                  totalWeight === 100
                    ? 'bg-status-success/15 text-status-success'
                    : 'bg-status-pending/15 text-status-pending'
                }`}
              >
                Sum: {totalWeight}%
              </span>
            </div>

            {/* Weights Sliders */}
            <div className="space-y-4">
              {[
                { label: 'Proximity / Distance (km)', val: wDist, set: setWDist },
                { label: 'Customer Rating (Stars)', val: wRating, set: setWRating },
                { label: 'Workload & Availability', val: wWorkload, set: setWWorkload },
                { label: 'Skill Certification Match', val: wSkill, set: setWSkill },
                { label: 'Historical Acceptance Rate', val: wAccept, set: setWAccept },
              ].map((item, idx) => (
                <div key={idx} className="space-y-1 text-xs">
                  <div className="flex justify-between font-semibold text-text">
                    <span>{item.label}</span>
                    <span className="font-bold text-primary">
                      {Math.round(item.val * 100)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={item.val}
                    onChange={(e) => item.set(parseFloat(e.target.value))}
                    className="w-full accent-primary cursor-pointer"
                  />
                </div>
              ))}
            </div>

            {/* Timeouts and Thresholds */}
            <div className="pt-4 border-t border-border grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-text mb-1">
                  Offer Timeout (Secs)
                </label>
                <input
                  type="number"
                  min="30"
                  max="300"
                  value={offerTimeout}
                  onChange={(e) => setOfferTimeout(parseInt(e.target.value) || 120)}
                  className="w-full px-3 py-2 rounded-input bg-surface text-text border border-border text-xs min-h-[44px]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-text mb-1">
                  High-Risk Timeout (Secs)
                </label>
                <input
                  type="number"
                  min="20"
                  max="180"
                  value={highRiskTimeout}
                  onChange={(e) => setHighRiskTimeout(parseInt(e.target.value) || 60)}
                  className="w-full px-3 py-2 rounded-input bg-surface text-text border border-border text-xs min-h-[44px]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-text mb-1">
                  Max Dispatch Attempts
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={maxAttempts}
                  onChange={(e) => setMaxAttempts(parseInt(e.target.value) || 5)}
                  className="w-full px-3 py-2 rounded-input bg-surface text-text border border-border text-xs min-h-[44px]"
                />
              </div>
            </div>

            <div className="flex justify-end pt-3">
              <Button variant="primary" size="md" type="submit" loading={savingConfig}>
                Save Engine Configuration
              </Button>
            </div>
          </Card>
        </form>
      ) : activeTab === 'categories' ? (
        <Card padding="lg" className="space-y-4 border-border">
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <h3 className="text-sm font-bold text-text">Service Categories Catalog</h3>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setCatModalOpen(true)}
              icon={<span>＋</span>}
            >
              Add Category
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {categories.map((c) => (
              <div
                key={c.id}
                className="p-3.5 rounded-card bg-surface-alt border border-border flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{c.icon || '🛠️'}</span>
                  <div>
                    <div className="font-bold text-xs text-text">{c.name}</div>
                    <div className="text-[11px] text-text-muted mt-0.5">
                      Rate: ₹{c.price_per_minute * 10}/hr • Cert L{c.required_certification_level}+
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : (
        <Card padding="lg" className="space-y-4 border-border">
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <h3 className="text-sm font-bold text-text">Configured SLA Targets</h3>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setTierModalOpen(true)}
              icon={<span>＋</span>}
            >
              New SLA Tier
            </Button>
          </div>

          <div className="space-y-2.5">
            {tiers.map((t) => (
              <div
                key={t.id}
                className="p-4 rounded-card bg-surface-alt border border-border flex items-center justify-between text-xs"
              >
                <div>
                  <div className="font-bold text-text flex items-center gap-2">
                    <span>{t.name}</span>
                    {t.is_default && (
                      <span className="text-[10px] bg-primary-tint text-primary px-1.5 py-0.5 rounded font-bold uppercase">
                        Default
                      </span>
                    )}
                  </div>
                  <div className="text-text-muted mt-0.5">
                    Response: {t.response_time_minutes}m • Resolution: {t.resolution_time_minutes}m
                  </div>
                </div>
                <span className="font-bold text-primary">Priority Level {t.priority_level}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Add Category Modal */}
      <Modal
        isOpen={catModalOpen}
        onClose={() => setCatModalOpen(false)}
        title="Add Service Category"
        description="Register a new appliance or service type in the customer catalog."
      >
        <form onSubmit={handleCreateCategory} className="space-y-4 py-2">
          <Input
            label="Category Name *"
            required
            value={catName}
            onChange={(e) => setCatName(e.target.value)}
            placeholder="e.g. Microwave Oven Repair"
          />
          <Input
            label="Description"
            value={catDesc}
            onChange={(e) => setCatDesc(e.target.value)}
            placeholder="Comprehensive diagnostic & heating element replacement"
          />
          <div className="grid grid-cols-3 gap-3">
            <Input
              label="Icon (Emoji)"
              value={catIcon}
              onChange={(e) => setCatIcon(e.target.value)}
            />
            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Rate / Min
              </label>
              <input
                type="number"
                step="0.5"
                value={catRate}
                onChange={(e) => setCatRate(parseFloat(e.target.value) || 2.0)}
                className="w-full min-h-[44px] px-3.5 py-2.5 rounded-input bg-surface text-text border border-border text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Min Cert (1-5)
              </label>
              <input
                type="number"
                min="1"
                max="5"
                value={catCert}
                onChange={(e) => setCatCert(parseInt(e.target.value) || 1)}
                className="w-full min-h-[44px] px-3.5 py-2.5 rounded-input bg-surface text-text border border-border text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button variant="secondary" size="md" onClick={() => setCatModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="md" type="submit" loading={savingCat}>
              Create Category
            </Button>
          </div>
        </form>
      </Modal>

      {/* Add SLA Tier Modal */}
      <Modal
        isOpen={tierModalOpen}
        onClose={() => setTierModalOpen(false)}
        title="Add SLA Tier"
        description="Define strict response and resolution thresholds by priority level."
      >
        <form onSubmit={handleCreateTier} className="space-y-4 py-2">
          <Input
            label="Tier Name *"
            required
            value={tierName}
            onChange={(e) => setTierName(e.target.value)}
            placeholder="e.g. VIP Urgent"
          />
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Priority Level (1-4)
              </label>
              <input
                type="number"
                min="1"
                max="4"
                value={tierPriority}
                onChange={(e) => setTierPriority(parseInt(e.target.value) || 2)}
                className="w-full min-h-[44px] px-3.5 py-2.5 rounded-input bg-surface text-text border border-border text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Response Target (min)
              </label>
              <input
                type="number"
                value={tierResponse}
                onChange={(e) => setTierResponse(parseInt(e.target.value) || 30)}
                className="w-full min-h-[44px] px-3.5 py-2.5 rounded-input bg-surface text-text border border-border text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Resolution Target (min)
              </label>
              <input
                type="number"
                value={tierResolution}
                onChange={(e) => setTierResolution(parseInt(e.target.value) || 120)}
                className="w-full min-h-[44px] px-3.5 py-2.5 rounded-input bg-surface text-text border border-border text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button variant="secondary" size="md" onClick={() => setTierModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="md" type="submit" loading={savingTier}>
              Create SLA Tier
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

