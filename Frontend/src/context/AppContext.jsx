import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api/client';

const AppContext = createContext();

export const useAppContext = () => useContext(AppContext);

export const AppProvider = ({ children }) => {
  const [members, setMembers] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [claims, setClaims] = useState([]);
  const [disputes, setDisputes] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const membersData = await api.getMembers();
      setMembers(membersData);

      // Fetch claims and policies for all members
      let allClaims = [];
      let allDisputes = [];
      let allPolicies = [];

      for (const member of membersData) {
        try {
          // Note: Backend might throw 404 if no policy/claims exist, so we catch individual errors
          const memberClaims = await api.getMemberClaims(member.member_id).catch(() => []);
          allClaims = [...allClaims, ...memberClaims];

          const memberPolicy = await fetch(`http://0.0.0.0:8000/api/v1/members/${member.member_id}/policy`)
            .then(res => res.ok ? res.json() : null)
            .catch(() => null);
            
          if (memberPolicy) {
            allPolicies.push(memberPolicy);
          }

          for (const claim of memberClaims) {
            const claimDisputes = await api.getClaimDisputes(claim.claim_id).catch(() => []);
            allDisputes = [...allDisputes, ...claimDisputes];
          }
        } catch (e) {
          console.error(`Error fetching data for member ${member.member_id}`, e);
        }
      }

      setClaims(allClaims);
      setPolicies(allPolicies);
      setDisputes(allDisputes);
    } catch (error) {
      console.error('Failed to load initial data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const addMember = async (memberData) => {
    try {
      const newMember = await api.createMember(memberData);
      setMembers([newMember, ...members]);
      return newMember;
    } catch (error) {
      console.error('Failed to create member:', error);
      throw error;
    }
  };

  const addPolicy = async (policyData) => {
    try {
      const newPolicy = await api.createPolicy(policyData);
      setPolicies([newPolicy, ...policies]);
      return newPolicy;
    } catch (error) {
      console.error('Failed to create policy:', error);
      throw error;
    }
  };

  const submitClaim = async (claimData) => {
    try {
      const newClaim = await api.submitClaim(claimData);
      setClaims([newClaim, ...claims]);
      return newClaim;
    } catch (error) {
      console.error('Failed to submit claim:', error);
      throw error;
    }
  };

  const fileDispute = async (claimId, disputeData) => {
    try {
      const newDispute = await api.createDispute(claimId, disputeData);
      setDisputes([newDispute, ...disputes]);
      return newDispute;
    } catch (error) {
      console.error('Failed to file dispute:', error);
      throw error;
    }
  };

  const getAdjudication = async (claimId) => {
    try {
      return await api.getClaimAdjudication(claimId);
    } catch (error) {
      console.error('Failed to get adjudication:', error);
      throw error;
    }
  };

  const getExplanation = async (claimId) => {
    try {
      return await api.getClaimExplanation(claimId);
    } catch (error) {
      console.error('Failed to get explanation:', error);
      throw error;
    }
  };

  const value = {
    members, addMember,
    policies, addPolicy,
    claims, submitClaim, getAdjudication, getExplanation,
    disputes, fileDispute,
    loading
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
};
