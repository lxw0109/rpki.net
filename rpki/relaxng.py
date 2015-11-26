# Automatically generated, do not edit.

from rpki.relaxng_parser import RelaxNGParser

## @var left_right
## Parsed RelaxNG left_right schema
left_right = RelaxNGParser(r'''<?xml version="1.0" encoding="UTF-8"?>
<!--
  $Id: left-right-schema.rnc 5902 2014-07-18 16:37:04Z sra $
  
  RelaxNG schema for RPKI left-right protocol.
  
  Copyright (C) 2012- -2014  Dragon Research Labs ("DRL")
  Portions copyright (C) 2009- -2011  Internet Systems Consortium ("ISC")
  Portions copyright (C) 2007- -2008  American Registry for Internet Numbers ("ARIN")
  
  Permission to use, copy, modify, and distribute this software for any
  purpose with or without fee is hereby granted, provided that the above
  copyright notices and this permission notice appear in all copies.
  
  THE SOFTWARE IS PROVIDED "AS IS" AND DRL, ISC, AND ARIN DISCLAIM ALL
  WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
  WARRANTIES OF MERCHANTABILITY AND FITNESS.  IN NO EVENT SHALL DRL,
  ISC, OR ARIN BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR
  CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
  OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
  NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
  WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
-->
<grammar ns="http://www.hactrn.net/uris/rpki/left-right-spec/" xmlns="http://relaxng.org/ns/structure/1.0" datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
  <define name="version">
    <value>1</value>
  </define>
  <!-- Top level PDU -->
  <start>
    <element name="msg">
      <attribute name="version">
        <data type="positiveInteger">
          <param name="maxInclusive">1</param>
        </data>
      </attribute>
      <choice>
        <group>
          <attribute name="type">
            <value>query</value>
          </attribute>
          <zeroOrMore>
            <ref name="query_elt"/>
          </zeroOrMore>
        </group>
        <group>
          <attribute name="type">
            <value>reply</value>
          </attribute>
          <zeroOrMore>
            <ref name="reply_elt"/>
          </zeroOrMore>
        </group>
      </choice>
    </element>
  </start>
  <!-- PDUs allowed in a query -->
  <define name="query_elt" combine="choice">
    <ref name="self_query"/>
  </define>
  <define name="query_elt" combine="choice">
    <ref name="bsc_query"/>
  </define>
  <define name="query_elt" combine="choice">
    <ref name="parent_query"/>
  </define>
  <define name="query_elt" combine="choice">
    <ref name="child_query"/>
  </define>
  <define name="query_elt" combine="choice">
    <ref name="repository_query"/>
  </define>
  <define name="query_elt" combine="choice">
    <ref name="list_roa_requests_query"/>
  </define>
  <define name="query_elt" combine="choice">
    <ref name="list_ghostbuster_requests_query"/>
  </define>
  <define name="query_elt" combine="choice">
    <ref name="list_ee_certificate_requests_query"/>
  </define>
  <define name="query_elt" combine="choice">
    <ref name="list_resources_query"/>
  </define>
  <define name="query_elt" combine="choice">
    <ref name="list_published_objects_query"/>
  </define>
  <define name="query_elt" combine="choice">
    <ref name="list_received_resources_query"/>
  </define>
  <!-- PDUs allowed in a reply -->
  <define name="reply_elt" combine="choice">
    <ref name="self_reply"/>
  </define>
  <define name="reply_elt" combine="choice">
    <ref name="bsc_reply"/>
  </define>
  <define name="reply_elt" combine="choice">
    <ref name="parent_reply"/>
  </define>
  <define name="reply_elt" combine="choice">
    <ref name="child_reply"/>
  </define>
  <define name="reply_elt" combine="choice">
    <ref name="repository_reply"/>
  </define>
  <define name="reply_elt" combine="choice">
    <ref name="list_resources_reply"/>
  </define>
  <define name="reply_elt" combine="choice">
    <ref name="list_roa_requests_reply"/>
  </define>
  <define name="reply_elt" combine="choice">
    <ref name="list_ghostbuster_requests_reply"/>
  </define>
  <define name="reply_elt" combine="choice">
    <ref name="list_ee_certificate_requests_reply"/>
  </define>
  <define name="reply_elt" combine="choice">
    <ref name="list_published_objects_reply"/>
  </define>
  <define name="reply_elt" combine="choice">
    <ref name="list_received_resources_reply"/>
  </define>
  <define name="reply_elt" combine="choice">
    <ref name="report_error_reply"/>
  </define>
  <!-- Tag attributes for bulk operations -->
  <define name="tag">
    <optional>
      <attribute name="tag">
        <data type="token">
          <param name="maxLength">1024</param>
        </data>
      </attribute>
    </optional>
  </define>
  <!--
    Combinations of action and type attributes used in later definitions.
    The same patterns repeat in most of the elements in this protocol.
  -->
  <define name="ctl_create">
    <attribute name="action">
      <value>create</value>
    </attribute>
    <ref name="tag"/>
  </define>
  <define name="ctl_set">
    <attribute name="action">
      <value>set</value>
    </attribute>
    <ref name="tag"/>
  </define>
  <define name="ctl_get">
    <attribute name="action">
      <value>get</value>
    </attribute>
    <ref name="tag"/>
  </define>
  <define name="ctl_list">
    <attribute name="action">
      <value>list</value>
    </attribute>
    <ref name="tag"/>
  </define>
  <define name="ctl_destroy">
    <attribute name="action">
      <value>destroy</value>
    </attribute>
    <ref name="tag"/>
  </define>
  <!-- Base64 encoded DER stuff -->
  <define name="base64">
    <data type="base64Binary">
      <param name="maxLength">512000</param>
    </data>
  </define>
  <!--
    Base definition for all fields that are really just SQL primary indices
    sql_id = xsd:nonNegativeInteger
  -->
  <!--
    ...except that fields containing SQL primary indicies don't belong
    in this protocol, so they're turninging into handles.
    Length restriction is a MySQL implementation issue.
    Handles are case-insensitive (because SQL is, among other reasons).
  -->
  <define name="object_handle">
    <data type="string">
      <param name="maxLength">255</param>
      <param name="pattern">[\-_A-Za-z0-9]+</param>
    </data>
  </define>
  <!-- URIs -->
  <define name="uri">
    <data type="anyURI">
      <param name="maxLength">4096</param>
    </data>
  </define>
  <!-- Name fields imported from up-down protocol -->
  <define name="up_down_name">
    <data type="token">
      <param name="maxLength">1024</param>
    </data>
  </define>
  <!-- Resource lists -->
  <define name="asn_list">
    <data type="string">
      <param name="maxLength">512000</param>
      <param name="pattern">[\-,0-9]*</param>
    </data>
  </define>
  <define name="ipv4_list">
    <data type="string">
      <param name="maxLength">512000</param>
      <param name="pattern">[\-,0-9/.]*</param>
    </data>
  </define>
  <define name="ipv6_list">
    <data type="string">
      <param name="maxLength">512000</param>
      <param name="pattern">[\-,0-9/:a-fA-F]*</param>
    </data>
  </define>
  <!-- <self/> element -->
  <define name="self_bool">
    <optional>
      <attribute name="rekey">
        <value>yes</value>
      </attribute>
    </optional>
    <optional>
      <attribute name="reissue">
        <value>yes</value>
      </attribute>
    </optional>
    <optional>
      <attribute name="revoke">
        <value>yes</value>
      </attribute>
    </optional>
    <optional>
      <attribute name="run_now">
        <value>yes</value>
      </attribute>
    </optional>
    <optional>
      <attribute name="publish_world_now">
        <value>yes</value>
      </attribute>
    </optional>
    <optional>
      <attribute name="revoke_forgotten">
        <value>yes</value>
      </attribute>
    </optional>
    <optional>
      <attribute name="clear_replay_protection">
        <value>yes</value>
      </attribute>
    </optional>
  </define>
  <define name="self_payload">
    <optional>
      <attribute name="use_hsm">
        <choice>
          <value>yes</value>
          <value>no</value>
        </choice>
      </attribute>
    </optional>
    <optional>
      <attribute name="crl_interval">
        <data type="positiveInteger"/>
      </attribute>
    </optional>
    <optional>
      <attribute name="regen_margin">
        <data type="positiveInteger"/>
      </attribute>
    </optional>
    <optional>
      <element name="bpki_cert">
        <ref name="base64"/>
      </element>
    </optional>
    <optional>
      <element name="bpki_glue">
        <ref name="base64"/>
      </element>
    </optional>
  </define>
  <define name="self_handle">
    <attribute name="self_handle">
      <ref name="object_handle"/>
    </attribute>
  </define>
  <define name="self_query" combine="choice">
    <element name="self">
      <ref name="ctl_create"/>
      <ref name="self_handle"/>
      <ref name="self_bool"/>
      <ref name="self_payload"/>
    </element>
  </define>
  <define name="self_reply" combine="choice">
    <element name="self">
      <ref name="ctl_create"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <define name="self_query" combine="choice">
    <element name="self">
      <ref name="ctl_set"/>
      <ref name="self_handle"/>
      <ref name="self_bool"/>
      <ref name="self_payload"/>
    </element>
  </define>
  <define name="self_reply" combine="choice">
    <element name="self">
      <ref name="ctl_set"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <define name="self_query" combine="choice">
    <element name="self">
      <ref name="ctl_get"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <define name="self_reply" combine="choice">
    <element name="self">
      <ref name="ctl_get"/>
      <ref name="self_handle"/>
      <ref name="self_payload"/>
    </element>
  </define>
  <define name="self_query" combine="choice">
    <element name="self">
      <ref name="ctl_list"/>
    </element>
  </define>
  <define name="self_reply" combine="choice">
    <element name="self">
      <ref name="ctl_list"/>
      <ref name="self_handle"/>
      <ref name="self_payload"/>
    </element>
  </define>
  <define name="self_query" combine="choice">
    <element name="self">
      <ref name="ctl_destroy"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <define name="self_reply" combine="choice">
    <element name="self">
      <ref name="ctl_destroy"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <!-- <bsc/> element.  Key parameters hardwired for now. -->
  <define name="bsc_bool">
    <optional>
      <attribute name="generate_keypair">
        <value>yes</value>
      </attribute>
      <optional>
        <attribute name="key_type">
          <value>rsa</value>
        </attribute>
      </optional>
      <optional>
        <attribute name="hash_alg">
          <value>sha256</value>
        </attribute>
      </optional>
      <optional>
        <attribute name="key_length">
          <value>2048</value>
        </attribute>
      </optional>
    </optional>
  </define>
  <define name="bsc_handle">
    <attribute name="bsc_handle">
      <ref name="object_handle"/>
    </attribute>
  </define>
  <define name="bsc_payload">
    <optional>
      <element name="signing_cert">
        <ref name="base64"/>
      </element>
    </optional>
    <optional>
      <element name="signing_cert_crl">
        <ref name="base64"/>
      </element>
    </optional>
  </define>
  <define name="bsc_readonly">
    <optional>
      <element name="pkcs10_request">
        <ref name="base64"/>
      </element>
    </optional>
  </define>
  <define name="bsc_query" combine="choice">
    <element name="bsc">
      <ref name="ctl_create"/>
      <ref name="self_handle"/>
      <ref name="bsc_handle"/>
      <ref name="bsc_bool"/>
      <ref name="bsc_payload"/>
    </element>
  </define>
  <define name="bsc_reply" combine="choice">
    <element name="bsc">
      <ref name="ctl_create"/>
      <ref name="self_handle"/>
      <ref name="bsc_handle"/>
      <ref name="bsc_readonly"/>
    </element>
  </define>
  <define name="bsc_query" combine="choice">
    <element name="bsc">
      <ref name="ctl_set"/>
      <ref name="self_handle"/>
      <ref name="bsc_handle"/>
      <ref name="bsc_bool"/>
      <ref name="bsc_payload"/>
    </element>
  </define>
  <define name="bsc_reply" combine="choice">
    <element name="bsc">
      <ref name="ctl_set"/>
      <ref name="self_handle"/>
      <ref name="bsc_handle"/>
      <ref name="bsc_readonly"/>
    </element>
  </define>
  <define name="bsc_query" combine="choice">
    <element name="bsc">
      <ref name="ctl_get"/>
      <ref name="self_handle"/>
      <ref name="bsc_handle"/>
    </element>
  </define>
  <define name="bsc_reply" combine="choice">
    <element name="bsc">
      <ref name="ctl_get"/>
      <ref name="self_handle"/>
      <ref name="bsc_handle"/>
      <ref name="bsc_payload"/>
      <ref name="bsc_readonly"/>
    </element>
  </define>
  <define name="bsc_query" combine="choice">
    <element name="bsc">
      <ref name="ctl_list"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <define name="bsc_reply" combine="choice">
    <element name="bsc">
      <ref name="ctl_list"/>
      <ref name="self_handle"/>
      <ref name="bsc_handle"/>
      <ref name="bsc_payload"/>
      <ref name="bsc_readonly"/>
    </element>
  </define>
  <define name="bsc_query" combine="choice">
    <element name="bsc">
      <ref name="ctl_destroy"/>
      <ref name="self_handle"/>
      <ref name="bsc_handle"/>
    </element>
  </define>
  <define name="bsc_reply" combine="choice">
    <element name="bsc">
      <ref name="ctl_destroy"/>
      <ref name="self_handle"/>
      <ref name="bsc_handle"/>
    </element>
  </define>
  <!-- <parent/> element -->
  <define name="parent_handle">
    <attribute name="parent_handle">
      <ref name="object_handle"/>
    </attribute>
  </define>
  <define name="parent_bool">
    <optional>
      <attribute name="rekey">
        <value>yes</value>
      </attribute>
    </optional>
    <optional>
      <attribute name="reissue">
        <value>yes</value>
      </attribute>
    </optional>
    <optional>
      <attribute name="revoke">
        <value>yes</value>
      </attribute>
    </optional>
    <optional>
      <attribute name="revoke_forgotten">
        <value>yes</value>
      </attribute>
    </optional>
    <optional>
      <attribute name="clear_replay_protection">
        <value>yes</value>
      </attribute>
    </optional>
  </define>
  <define name="parent_payload">
    <optional>
      <attribute name="peer_contact_uri">
        <ref name="uri"/>
      </attribute>
    </optional>
    <optional>
      <attribute name="sia_base">
        <ref name="uri"/>
      </attribute>
    </optional>
    <optional>
      <ref name="bsc_handle"/>
    </optional>
    <optional>
      <ref name="repository_handle"/>
    </optional>
    <optional>
      <attribute name="sender_name">
        <ref name="up_down_name"/>
      </attribute>
    </optional>
    <optional>
      <attribute name="recipient_name">
        <ref name="up_down_name"/>
      </attribute>
    </optional>
    <optional>
      <element name="bpki_cms_cert">
        <ref name="base64"/>
      </element>
    </optional>
    <optional>
      <element name="bpki_cms_glue">
        <ref name="base64"/>
      </element>
    </optional>
  </define>
  <define name="parent_query" combine="choice">
    <element name="parent">
      <ref name="ctl_create"/>
      <ref name="self_handle"/>
      <ref name="parent_handle"/>
      <ref name="parent_bool"/>
      <ref name="parent_payload"/>
    </element>
  </define>
  <define name="parent_reply" combine="choice">
    <element name="parent">
      <ref name="ctl_create"/>
      <ref name="self_handle"/>
      <ref name="parent_handle"/>
    </element>
  </define>
  <define name="parent_query" combine="choice">
    <element name="parent">
      <ref name="ctl_set"/>
      <ref name="self_handle"/>
      <ref name="parent_handle"/>
      <ref name="parent_bool"/>
      <ref name="parent_payload"/>
    </element>
  </define>
  <define name="parent_reply" combine="choice">
    <element name="parent">
      <ref name="ctl_set"/>
      <ref name="self_handle"/>
      <ref name="parent_handle"/>
    </element>
  </define>
  <define name="parent_query" combine="choice">
    <element name="parent">
      <ref name="ctl_get"/>
      <ref name="self_handle"/>
      <ref name="parent_handle"/>
    </element>
  </define>
  <define name="parent_reply" combine="choice">
    <element name="parent">
      <ref name="ctl_get"/>
      <ref name="self_handle"/>
      <ref name="parent_handle"/>
      <ref name="parent_payload"/>
    </element>
  </define>
  <define name="parent_query" combine="choice">
    <element name="parent">
      <ref name="ctl_list"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <define name="parent_reply" combine="choice">
    <element name="parent">
      <ref name="ctl_list"/>
      <ref name="self_handle"/>
      <ref name="parent_handle"/>
      <ref name="parent_payload"/>
    </element>
  </define>
  <define name="parent_query" combine="choice">
    <element name="parent">
      <ref name="ctl_destroy"/>
      <ref name="self_handle"/>
      <ref name="parent_handle"/>
    </element>
  </define>
  <define name="parent_reply" combine="choice">
    <element name="parent">
      <ref name="ctl_destroy"/>
      <ref name="self_handle"/>
      <ref name="parent_handle"/>
    </element>
  </define>
  <!-- <child/> element -->
  <define name="child_handle">
    <attribute name="child_handle">
      <ref name="object_handle"/>
    </attribute>
  </define>
  <define name="child_bool">
    <optional>
      <attribute name="reissue">
        <value>yes</value>
      </attribute>
    </optional>
    <optional>
      <attribute name="clear_replay_protection">
        <value>yes</value>
      </attribute>
    </optional>
  </define>
  <define name="child_payload">
    <optional>
      <ref name="bsc_handle"/>
    </optional>
    <optional>
      <element name="bpki_cert">
        <ref name="base64"/>
      </element>
    </optional>
    <optional>
      <element name="bpki_glue">
        <ref name="base64"/>
      </element>
    </optional>
  </define>
  <define name="child_query" combine="choice">
    <element name="child">
      <ref name="ctl_create"/>
      <ref name="self_handle"/>
      <ref name="child_handle"/>
      <ref name="child_bool"/>
      <ref name="child_payload"/>
    </element>
  </define>
  <define name="child_reply" combine="choice">
    <element name="child">
      <ref name="ctl_create"/>
      <ref name="self_handle"/>
      <ref name="child_handle"/>
    </element>
  </define>
  <define name="child_query" combine="choice">
    <element name="child">
      <ref name="ctl_set"/>
      <ref name="self_handle"/>
      <ref name="child_handle"/>
      <ref name="child_bool"/>
      <ref name="child_payload"/>
    </element>
  </define>
  <define name="child_reply" combine="choice">
    <element name="child">
      <ref name="ctl_set"/>
      <ref name="self_handle"/>
      <ref name="child_handle"/>
    </element>
  </define>
  <define name="child_query" combine="choice">
    <element name="child">
      <ref name="ctl_get"/>
      <ref name="self_handle"/>
      <ref name="child_handle"/>
    </element>
  </define>
  <define name="child_reply" combine="choice">
    <element name="child">
      <ref name="ctl_get"/>
      <ref name="self_handle"/>
      <ref name="child_handle"/>
      <ref name="child_payload"/>
    </element>
  </define>
  <define name="child_query" combine="choice">
    <element name="child">
      <ref name="ctl_list"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <define name="child_reply" combine="choice">
    <element name="child">
      <ref name="ctl_list"/>
      <ref name="self_handle"/>
      <ref name="child_handle"/>
      <ref name="child_payload"/>
    </element>
  </define>
  <define name="child_query" combine="choice">
    <element name="child">
      <ref name="ctl_destroy"/>
      <ref name="self_handle"/>
      <ref name="child_handle"/>
    </element>
  </define>
  <define name="child_reply" combine="choice">
    <element name="child">
      <ref name="ctl_destroy"/>
      <ref name="self_handle"/>
      <ref name="child_handle"/>
    </element>
  </define>
  <!-- <repository/> element -->
  <define name="repository_handle">
    <attribute name="repository_handle">
      <ref name="object_handle"/>
    </attribute>
  </define>
  <define name="repository_bool">
    <optional>
      <attribute name="clear_replay_protection">
        <value>yes</value>
      </attribute>
    </optional>
  </define>
  <define name="repository_payload">
    <optional>
      <attribute name="peer_contact_uri">
        <ref name="uri"/>
      </attribute>
    </optional>
    <optional>
      <ref name="bsc_handle"/>
    </optional>
    <optional>
      <element name="bpki_cert">
        <ref name="base64"/>
      </element>
    </optional>
    <optional>
      <element name="bpki_glue">
        <ref name="base64"/>
      </element>
    </optional>
  </define>
  <define name="repository_query" combine="choice">
    <element name="repository">
      <ref name="ctl_create"/>
      <ref name="self_handle"/>
      <ref name="repository_handle"/>
      <ref name="repository_bool"/>
      <ref name="repository_payload"/>
    </element>
  </define>
  <define name="repository_reply" combine="choice">
    <element name="repository">
      <ref name="ctl_create"/>
      <ref name="self_handle"/>
      <ref name="repository_handle"/>
    </element>
  </define>
  <define name="repository_query" combine="choice">
    <element name="repository">
      <ref name="ctl_set"/>
      <ref name="self_handle"/>
      <ref name="repository_handle"/>
      <ref name="repository_bool"/>
      <ref name="repository_payload"/>
    </element>
  </define>
  <define name="repository_reply" combine="choice">
    <element name="repository">
      <ref name="ctl_set"/>
      <ref name="self_handle"/>
      <ref name="repository_handle"/>
    </element>
  </define>
  <define name="repository_query" combine="choice">
    <element name="repository">
      <ref name="ctl_get"/>
      <ref name="self_handle"/>
      <ref name="repository_handle"/>
    </element>
  </define>
  <define name="repository_reply" combine="choice">
    <element name="repository">
      <ref name="ctl_get"/>
      <ref name="self_handle"/>
      <ref name="repository_handle"/>
      <ref name="repository_payload"/>
    </element>
  </define>
  <define name="repository_query" combine="choice">
    <element name="repository">
      <ref name="ctl_list"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <define name="repository_reply" combine="choice">
    <element name="repository">
      <ref name="ctl_list"/>
      <ref name="self_handle"/>
      <ref name="repository_handle"/>
      <ref name="repository_payload"/>
    </element>
  </define>
  <define name="repository_query" combine="choice">
    <element name="repository">
      <ref name="ctl_destroy"/>
      <ref name="self_handle"/>
      <ref name="repository_handle"/>
    </element>
  </define>
  <define name="repository_reply" combine="choice">
    <element name="repository">
      <ref name="ctl_destroy"/>
      <ref name="self_handle"/>
      <ref name="repository_handle"/>
    </element>
  </define>
  <!-- <list_resources/> element -->
  <define name="list_resources_query">
    <element name="list_resources">
      <ref name="tag"/>
      <ref name="self_handle"/>
      <ref name="child_handle"/>
    </element>
  </define>
  <define name="list_resources_reply">
    <element name="list_resources">
      <ref name="tag"/>
      <ref name="self_handle"/>
      <ref name="child_handle"/>
      <attribute name="valid_until">
        <data type="dateTime">
          <param name="pattern">.*Z</param>
        </data>
      </attribute>
      <optional>
        <attribute name="asn">
          <ref name="asn_list"/>
        </attribute>
      </optional>
      <optional>
        <attribute name="ipv4">
          <ref name="ipv4_list"/>
        </attribute>
      </optional>
      <optional>
        <attribute name="ipv6">
          <ref name="ipv6_list"/>
        </attribute>
      </optional>
    </element>
  </define>
  <!-- <list_roa_requests/> element -->
  <define name="list_roa_requests_query">
    <element name="list_roa_requests">
      <ref name="tag"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <define name="list_roa_requests_reply">
    <element name="list_roa_requests">
      <ref name="tag"/>
      <ref name="self_handle"/>
      <attribute name="asn">
        <data type="nonNegativeInteger"/>
      </attribute>
      <optional>
        <attribute name="ipv4">
          <ref name="ipv4_list"/>
        </attribute>
      </optional>
      <optional>
        <attribute name="ipv6">
          <ref name="ipv6_list"/>
        </attribute>
      </optional>
    </element>
  </define>
  <!-- <list_ghostbuster_requests/> element -->
  <define name="list_ghostbuster_requests_query">
    <element name="list_ghostbuster_requests">
      <ref name="tag"/>
      <ref name="self_handle"/>
      <ref name="parent_handle"/>
    </element>
  </define>
  <define name="list_ghostbuster_requests_reply">
    <element name="list_ghostbuster_requests">
      <ref name="tag"/>
      <ref name="self_handle"/>
      <ref name="parent_handle"/>
      <data type="string"/>
    </element>
  </define>
  <!-- <list_ee_certificate_requests/> element -->
  <define name="list_ee_certificate_requests_query">
    <element name="list_ee_certificate_requests">
      <ref name="tag"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <define name="list_ee_certificate_requests_reply">
    <element name="list_ee_certificate_requests">
      <ref name="tag"/>
      <ref name="self_handle"/>
      <attribute name="gski">
        <data type="token">
          <param name="minLength">27</param>
          <param name="maxLength">27</param>
        </data>
      </attribute>
      <attribute name="valid_until">
        <data type="dateTime">
          <param name="pattern">.*Z</param>
        </data>
      </attribute>
      <optional>
        <attribute name="asn">
          <ref name="asn_list"/>
        </attribute>
      </optional>
      <optional>
        <attribute name="ipv4">
          <ref name="ipv4_list"/>
        </attribute>
      </optional>
      <optional>
        <attribute name="ipv6">
          <ref name="ipv6_list"/>
        </attribute>
      </optional>
      <optional>
        <attribute name="cn">
          <data type="string">
            <param name="maxLength">64</param>
            <param name="pattern">[\-0-9A-Za-z_ ]+</param>
          </data>
        </attribute>
      </optional>
      <optional>
        <attribute name="sn">
          <data type="string">
            <param name="maxLength">64</param>
            <param name="pattern">[0-9A-Fa-f]+</param>
          </data>
        </attribute>
      </optional>
      <optional>
        <attribute name="eku">
          <data type="string">
            <param name="maxLength">512000</param>
            <param name="pattern">[.,0-9]+</param>
          </data>
        </attribute>
      </optional>
      <element name="pkcs10">
        <ref name="base64"/>
      </element>
    </element>
  </define>
  <!-- <list_published_objects/> element -->
  <define name="list_published_objects_query">
    <element name="list_published_objects">
      <ref name="tag"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <define name="list_published_objects_reply">
    <element name="list_published_objects">
      <ref name="tag"/>
      <ref name="self_handle"/>
      <attribute name="uri">
        <ref name="uri"/>
      </attribute>
      <optional>
        <attribute name="child_handle">
          <ref name="object_handle"/>
        </attribute>
      </optional>
      <ref name="base64"/>
    </element>
  </define>
  <!-- <list_received_resources/> element -->
  <define name="list_received_resources_query">
    <element name="list_received_resources">
      <ref name="tag"/>
      <ref name="self_handle"/>
    </element>
  </define>
  <define name="list_received_resources_reply">
    <element name="list_received_resources">
      <ref name="tag"/>
      <ref name="self_handle"/>
      <ref name="parent_handle"/>
      <attribute name="notBefore">
        <data type="dateTime">
          <param name="pattern">.*Z</param>
        </data>
      </attribute>
      <attribute name="notAfter">
        <data type="dateTime">
          <param name="pattern">.*Z</param>
        </data>
      </attribute>
      <attribute name="uri">
        <ref name="uri"/>
      </attribute>
      <attribute name="sia_uri">
        <ref name="uri"/>
      </attribute>
      <attribute name="aia_uri">
        <ref name="uri"/>
      </attribute>
      <optional>
        <attribute name="asn">
          <ref name="asn_list"/>
        </attribute>
      </optional>
      <optional>
        <attribute name="ipv4">
          <ref name="ipv4_list"/>
        </attribute>
      </optional>
      <optional>
        <attribute name="ipv6">
          <ref name="ipv6_list"/>
        </attribute>
      </optional>
    </element>
  </define>
  <!-- <report_error/> element -->
  <define name="error">
    <data type="token">
      <param name="maxLength">1024</param>
    </data>
  </define>
  <define name="report_error_reply">
    <element name="report_error">
      <ref name="tag"/>
      <optional>
        <ref name="self_handle"/>
      </optional>
      <attribute name="error_code">
        <ref name="error"/>
      </attribute>
      <optional>
        <data type="string">
          <param name="maxLength">512000</param>
        </data>
      </optional>
    </element>
  </define>
</grammar>
<!--
  Local Variables:
  indent-tabs-mode: nil
  comment-start: "# "
  comment-start-skip: "#[ \t]*"
  End:
-->
''')

## @var myrpki
## Parsed RelaxNG myrpki schema
myrpki = RelaxNGParser(r'''<?xml version="1.0" encoding="UTF-8"?>
<!--
  $Id: myrpki.rnc 5757 2014-04-05 22:42:12Z sra $
  
  RelaxNG schema for MyRPKI XML messages.
  
  This message protocol is on its way out, as we're in the process of
  moving on from the user interface model that produced it, but even
  after we finish replacing it we'll still need the schema for a while
  to validate old messages when upgrading.
  
  libxml2 (including xmllint) only groks the XML syntax of RelaxNG, so
  run the compact syntax through trang to get XML syntax.
  
  Copyright (C) 2009-2011  Internet Systems Consortium ("ISC")
  
  Permission to use, copy, modify, and distribute this software for any
  purpose with or without fee is hereby granted, provided that the above
  copyright notice and this permission notice appear in all copies.
  
  THE SOFTWARE IS PROVIDED "AS IS" AND ISC DISCLAIMS ALL WARRANTIES WITH
  REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
  AND FITNESS.  IN NO EVENT SHALL ISC BE LIABLE FOR ANY SPECIAL, DIRECT,
  INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
  LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
  OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
  PERFORMANCE OF THIS SOFTWARE.
-->
<grammar ns="http://www.hactrn.net/uris/rpki/myrpki/" xmlns="http://relaxng.org/ns/structure/1.0" datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
  <define name="version">
    <value>2</value>
  </define>
  <define name="base64">
    <data type="base64Binary">
      <param name="maxLength">512000</param>
    </data>
  </define>
  <define name="object_handle">
    <data type="string">
      <param name="maxLength">255</param>
      <param name="pattern">[\-_A-Za-z0-9]+</param>
    </data>
  </define>
  <define name="pubd_handle">
    <data type="string">
      <param name="maxLength">255</param>
      <param name="pattern">[\-_A-Za-z0-9/]+</param>
    </data>
  </define>
  <define name="uri">
    <data type="anyURI">
      <param name="maxLength">4096</param>
    </data>
  </define>
  <define name="asn">
    <data type="positiveInteger"/>
  </define>
  <define name="asn_list">
    <data type="string">
      <param name="maxLength">512000</param>
      <param name="pattern">[\-,0-9]+</param>
    </data>
  </define>
  <define name="ipv4_list">
    <data type="string">
      <param name="maxLength">512000</param>
      <param name="pattern">[\-,0-9/.]+</param>
    </data>
  </define>
  <define name="ipv6_list">
    <data type="string">
      <param name="maxLength">512000</param>
      <param name="pattern">[\-,0-9/:a-fA-F]+</param>
    </data>
  </define>
  <define name="timestamp">
    <data type="dateTime">
      <param name="pattern">.*Z</param>
    </data>
  </define>
  <!--
    Message formate used between configure_resources and
    configure_daemons.
  -->
  <start combine="choice">
    <element name="myrpki">
      <attribute name="version">
        <ref name="version"/>
      </attribute>
      <attribute name="handle">
        <ref name="object_handle"/>
      </attribute>
      <optional>
        <attribute name="service_uri">
          <ref name="uri"/>
        </attribute>
      </optional>
      <zeroOrMore>
        <element name="roa_request">
          <attribute name="asn">
            <ref name="asn"/>
          </attribute>
          <attribute name="v4">
            <ref name="ipv4_list"/>
          </attribute>
          <attribute name="v6">
            <ref name="ipv6_list"/>
          </attribute>
        </element>
      </zeroOrMore>
      <zeroOrMore>
        <element name="child">
          <attribute name="handle">
            <ref name="object_handle"/>
          </attribute>
          <attribute name="valid_until">
            <ref name="timestamp"/>
          </attribute>
          <optional>
            <attribute name="asns">
              <ref name="asn_list"/>
            </attribute>
          </optional>
          <optional>
            <attribute name="v4">
              <ref name="ipv4_list"/>
            </attribute>
          </optional>
          <optional>
            <attribute name="v6">
              <ref name="ipv6_list"/>
            </attribute>
          </optional>
          <optional>
            <element name="bpki_certificate">
              <ref name="base64"/>
            </element>
          </optional>
        </element>
      </zeroOrMore>
      <zeroOrMore>
        <element name="parent">
          <attribute name="handle">
            <ref name="object_handle"/>
          </attribute>
          <optional>
            <attribute name="service_uri">
              <ref name="uri"/>
            </attribute>
          </optional>
          <optional>
            <attribute name="myhandle">
              <ref name="object_handle"/>
            </attribute>
          </optional>
          <optional>
            <attribute name="sia_base">
              <ref name="uri"/>
            </attribute>
          </optional>
          <optional>
            <element name="bpki_cms_certificate">
              <ref name="base64"/>
            </element>
          </optional>
        </element>
      </zeroOrMore>
      <zeroOrMore>
        <element name="repository">
          <attribute name="handle">
            <ref name="object_handle"/>
          </attribute>
          <optional>
            <attribute name="service_uri">
              <ref name="uri"/>
            </attribute>
          </optional>
          <optional>
            <element name="bpki_certificate">
              <ref name="base64"/>
            </element>
          </optional>
        </element>
      </zeroOrMore>
      <optional>
        <element name="bpki_ca_certificate">
          <ref name="base64"/>
        </element>
      </optional>
      <optional>
        <element name="bpki_crl">
          <ref name="base64"/>
        </element>
      </optional>
      <optional>
        <element name="bpki_bsc_certificate">
          <ref name="base64"/>
        </element>
      </optional>
      <optional>
        <element name="bpki_bsc_pkcs10">
          <ref name="base64"/>
        </element>
      </optional>
    </element>
  </start>
  <!-- Format of an identity.xml file. -->
  <start combine="choice">
    <element name="identity">
      <attribute name="version">
        <ref name="version"/>
      </attribute>
      <attribute name="handle">
        <ref name="object_handle"/>
      </attribute>
      <element name="bpki_ta">
        <ref name="base64"/>
      </element>
    </element>
  </start>
  <!--
    Format of <authorization/> element used in referrals.  The Base64
    text is a <referral/> (q. v.) element signed with CMS.
  -->
  <define name="authorization">
    <element name="authorization">
      <attribute name="referrer">
        <ref name="pubd_handle"/>
      </attribute>
      <ref name="base64"/>
    </element>
  </define>
  <!-- Format of <contact_info/> element used in referrals. -->
  <define name="contact_info">
    <element name="contact_info">
      <optional>
        <attribute name="uri">
          <ref name="uri"/>
        </attribute>
      </optional>
      <data type="string"/>
    </element>
  </define>
  <!-- Variant payload portion of a <repository/> element. -->
  <define name="repository_payload">
    <choice>
      <attribute name="type">
        <value>none</value>
      </attribute>
      <attribute name="type">
        <value>offer</value>
      </attribute>
      <group>
        <attribute name="type">
          <value>referral</value>
        </attribute>
        <ref name="authorization"/>
        <ref name="contact_info"/>
      </group>
    </choice>
  </define>
  <!-- <parent/> element (response from configure_child). -->
  <start combine="choice">
    <element name="parent">
      <attribute name="version">
        <ref name="version"/>
      </attribute>
      <optional>
        <attribute name="valid_until">
          <ref name="timestamp"/>
        </attribute>
      </optional>
      <optional>
        <attribute name="service_uri">
          <ref name="uri"/>
        </attribute>
      </optional>
      <attribute name="child_handle">
        <ref name="object_handle"/>
      </attribute>
      <attribute name="parent_handle">
        <ref name="object_handle"/>
      </attribute>
      <element name="bpki_resource_ta">
        <ref name="base64"/>
      </element>
      <element name="bpki_child_ta">
        <ref name="base64"/>
      </element>
      <optional>
        <element name="repository">
          <ref name="repository_payload"/>
        </element>
      </optional>
    </element>
  </start>
  <!--
    <repository/> element, types offer and referral
    (input to configure_publication_client).
  -->
  <start combine="choice">
    <element name="repository">
      <attribute name="version">
        <ref name="version"/>
      </attribute>
      <attribute name="handle">
        <ref name="object_handle"/>
      </attribute>
      <attribute name="parent_handle">
        <ref name="object_handle"/>
      </attribute>
      <ref name="repository_payload"/>
      <element name="bpki_client_ta">
        <ref name="base64"/>
      </element>
    </element>
  </start>
  <!--
    <repository/> element, confirmation type (output of
    configure_publication_client).
  -->
  <start combine="choice">
    <element name="repository">
      <attribute name="version">
        <ref name="version"/>
      </attribute>
      <attribute name="type">
        <value>confirmed</value>
      </attribute>
      <attribute name="parent_handle">
        <ref name="object_handle"/>
      </attribute>
      <attribute name="client_handle">
        <ref name="pubd_handle"/>
      </attribute>
      <attribute name="service_uri">
        <ref name="uri"/>
      </attribute>
      <attribute name="sia_base">
        <ref name="uri"/>
      </attribute>
      <element name="bpki_server_ta">
        <ref name="base64"/>
      </element>
      <element name="bpki_client_ta">
        <ref name="base64"/>
      </element>
      <optional>
        <ref name="authorization"/>
      </optional>
      <optional>
        <ref name="contact_info"/>
      </optional>
    </element>
  </start>
  <!--
    <referral/> element.  This is the entirety of a separate message
    which is signed with CMS then included ase the Base64 content of an
    <authorization/> element in the main message.
  -->
  <start combine="choice">
    <element name="referral">
      <attribute name="version">
        <ref name="version"/>
      </attribute>
      <attribute name="authorized_sia_base">
        <ref name="uri"/>
      </attribute>
      <ref name="base64"/>
    </element>
  </start>
</grammar>
<!--
  Local Variables:
  indent-tabs-mode: nil
  comment-start: "# "
  comment-start-skip: "#[ \t]*"
  End:
-->
''')

## @var publication
## Parsed RelaxNG publication schema
publication = RelaxNGParser(r'''<?xml version="1.0" encoding="UTF-8"?>
<!--
  $Id: publication-schema.rnc 5902 2014-07-18 16:37:04Z sra $
  
  RelaxNG schema for RPKI publication protocol.
  
  Copyright (C) 2012- -2014  Dragon Research Labs ("DRL")
  Portions copyright (C) 2009- -2011  Internet Systems Consortium ("ISC")
  Portions copyright (C) 2007- -2008  American Registry for Internet Numbers ("ARIN")
  
  Permission to use, copy, modify, and distribute this software for any
  purpose with or without fee is hereby granted, provided that the above
  copyright notices and this permission notice appear in all copies.
  
  THE SOFTWARE IS PROVIDED "AS IS" AND DRL, ISC, AND ARIN DISCLAIM ALL
  WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
  WARRANTIES OF MERCHANTABILITY AND FITNESS.  IN NO EVENT SHALL DRL,
  ISC, OR ARIN BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR
  CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
  OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
  NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
  WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
-->
<grammar ns="http://www.hactrn.net/uris/rpki/publication-spec/" xmlns="http://relaxng.org/ns/structure/1.0" datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
  <define name="version">
    <value>1</value>
  </define>
  <!-- Top level PDU -->
  <start>
    <element name="msg">
      <attribute name="version">
        <data type="positiveInteger">
          <param name="maxInclusive">1</param>
        </data>
      </attribute>
      <choice>
        <group>
          <attribute name="type">
            <value>query</value>
          </attribute>
          <zeroOrMore>
            <ref name="query_elt"/>
          </zeroOrMore>
        </group>
        <group>
          <attribute name="type">
            <value>reply</value>
          </attribute>
          <zeroOrMore>
            <ref name="reply_elt"/>
          </zeroOrMore>
        </group>
      </choice>
    </element>
  </start>
  <!-- PDUs allowed in a query -->
  <define name="query_elt">
    <choice>
      <ref name="config_query"/>
      <ref name="client_query"/>
      <ref name="certificate_query"/>
      <ref name="crl_query"/>
      <ref name="manifest_query"/>
      <ref name="roa_query"/>
      <ref name="ghostbuster_query"/>
    </choice>
  </define>
  <!-- PDUs allowed in a reply -->
  <define name="reply_elt">
    <choice>
      <ref name="config_reply"/>
      <ref name="client_reply"/>
      <ref name="certificate_reply"/>
      <ref name="crl_reply"/>
      <ref name="manifest_reply"/>
      <ref name="roa_reply"/>
      <ref name="ghostbuster_reply"/>
      <ref name="report_error_reply"/>
    </choice>
  </define>
  <!-- Tag attributes for bulk operations -->
  <define name="tag">
    <attribute name="tag">
      <data type="token">
        <param name="maxLength">1024</param>
      </data>
    </attribute>
  </define>
  <!--
    Base64 encoded DER stuff
    base64 = xsd:base64Binary { maxLength="512000" }
    
    Sadly, it turns out that CRLs can in fact get longer than this for an active CA.
    Remove length limit for now, think about whether to put it back later.
  -->
  <define name="base64">
    <data type="base64Binary"/>
  </define>
  <!-- Publication URLs -->
  <define name="uri_t">
    <data type="anyURI">
      <param name="maxLength">4096</param>
    </data>
  </define>
  <define name="uri">
    <attribute name="uri">
      <ref name="uri_t"/>
    </attribute>
  </define>
  <!--
    Handles on remote objects (replaces passing raw SQL IDs).  NB:
    Unlike the up-down protocol, handles in this protocol allow "/" as a
    hierarchy delimiter.
  -->
  <define name="object_handle">
    <data type="string">
      <param name="maxLength">255</param>
      <param name="pattern">[\-_A-Za-z0-9/]+</param>
    </data>
  </define>
  <!--
    <config/> element (use restricted to repository operator)
    config_handle attribute, create, list, and destroy commands omitted deliberately, see code for details
  -->
  <define name="config_payload">
    <optional>
      <element name="bpki_crl">
        <ref name="base64"/>
      </element>
    </optional>
  </define>
  <define name="config_query" combine="choice">
    <element name="config">
      <attribute name="action">
        <value>set</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="config_payload"/>
    </element>
  </define>
  <define name="config_reply" combine="choice">
    <element name="config">
      <attribute name="action">
        <value>set</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
    </element>
  </define>
  <define name="config_query" combine="choice">
    <element name="config">
      <attribute name="action">
        <value>get</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
    </element>
  </define>
  <define name="config_reply" combine="choice">
    <element name="config">
      <attribute name="action">
        <value>get</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="config_payload"/>
    </element>
  </define>
  <!-- <client/> element (use restricted to repository operator) -->
  <define name="client_handle">
    <attribute name="client_handle">
      <ref name="object_handle"/>
    </attribute>
  </define>
  <define name="client_bool">
    <optional>
      <attribute name="clear_replay_protection">
        <value>yes</value>
      </attribute>
    </optional>
  </define>
  <define name="client_payload">
    <optional>
      <attribute name="base_uri">
        <ref name="uri_t"/>
      </attribute>
    </optional>
    <optional>
      <element name="bpki_cert">
        <ref name="base64"/>
      </element>
    </optional>
    <optional>
      <element name="bpki_glue">
        <ref name="base64"/>
      </element>
    </optional>
  </define>
  <define name="client_query" combine="choice">
    <element name="client">
      <attribute name="action">
        <value>create</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="client_handle"/>
      <ref name="client_bool"/>
      <ref name="client_payload"/>
    </element>
  </define>
  <define name="client_reply" combine="choice">
    <element name="client">
      <attribute name="action">
        <value>create</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="client_handle"/>
    </element>
  </define>
  <define name="client_query" combine="choice">
    <element name="client">
      <attribute name="action">
        <value>set</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="client_handle"/>
      <ref name="client_bool"/>
      <ref name="client_payload"/>
    </element>
  </define>
  <define name="client_reply" combine="choice">
    <element name="client">
      <attribute name="action">
        <value>set</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="client_handle"/>
    </element>
  </define>
  <define name="client_query" combine="choice">
    <element name="client">
      <attribute name="action">
        <value>get</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="client_handle"/>
    </element>
  </define>
  <define name="client_reply" combine="choice">
    <element name="client">
      <attribute name="action">
        <value>get</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="client_handle"/>
      <ref name="client_payload"/>
    </element>
  </define>
  <define name="client_query" combine="choice">
    <element name="client">
      <attribute name="action">
        <value>list</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
    </element>
  </define>
  <define name="client_reply" combine="choice">
    <element name="client">
      <attribute name="action">
        <value>list</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="client_handle"/>
      <ref name="client_payload"/>
    </element>
  </define>
  <define name="client_query" combine="choice">
    <element name="client">
      <attribute name="action">
        <value>destroy</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="client_handle"/>
    </element>
  </define>
  <define name="client_reply" combine="choice">
    <element name="client">
      <attribute name="action">
        <value>destroy</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="client_handle"/>
    </element>
  </define>
  <!-- <certificate/> element -->
  <define name="certificate_query" combine="choice">
    <element name="certificate">
      <attribute name="action">
        <value>publish</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
      <ref name="base64"/>
    </element>
  </define>
  <define name="certificate_reply" combine="choice">
    <element name="certificate">
      <attribute name="action">
        <value>publish</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <define name="certificate_query" combine="choice">
    <element name="certificate">
      <attribute name="action">
        <value>withdraw</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <define name="certificate_reply" combine="choice">
    <element name="certificate">
      <attribute name="action">
        <value>withdraw</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <!-- <crl/> element -->
  <define name="crl_query" combine="choice">
    <element name="crl">
      <attribute name="action">
        <value>publish</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
      <ref name="base64"/>
    </element>
  </define>
  <define name="crl_reply" combine="choice">
    <element name="crl">
      <attribute name="action">
        <value>publish</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <define name="crl_query" combine="choice">
    <element name="crl">
      <attribute name="action">
        <value>withdraw</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <define name="crl_reply" combine="choice">
    <element name="crl">
      <attribute name="action">
        <value>withdraw</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <!-- <manifest/> element -->
  <define name="manifest_query" combine="choice">
    <element name="manifest">
      <attribute name="action">
        <value>publish</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
      <ref name="base64"/>
    </element>
  </define>
  <define name="manifest_reply" combine="choice">
    <element name="manifest">
      <attribute name="action">
        <value>publish</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <define name="manifest_query" combine="choice">
    <element name="manifest">
      <attribute name="action">
        <value>withdraw</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <define name="manifest_reply" combine="choice">
    <element name="manifest">
      <attribute name="action">
        <value>withdraw</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <!-- <roa/> element -->
  <define name="roa_query" combine="choice">
    <element name="roa">
      <attribute name="action">
        <value>publish</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
      <ref name="base64"/>
    </element>
  </define>
  <define name="roa_reply" combine="choice">
    <element name="roa">
      <attribute name="action">
        <value>publish</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <define name="roa_query" combine="choice">
    <element name="roa">
      <attribute name="action">
        <value>withdraw</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <define name="roa_reply" combine="choice">
    <element name="roa">
      <attribute name="action">
        <value>withdraw</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <!-- <ghostbuster/> element -->
  <define name="ghostbuster_query" combine="choice">
    <element name="ghostbuster">
      <attribute name="action">
        <value>publish</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
      <ref name="base64"/>
    </element>
  </define>
  <define name="ghostbuster_reply" combine="choice">
    <element name="ghostbuster">
      <attribute name="action">
        <value>publish</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <define name="ghostbuster_query" combine="choice">
    <element name="ghostbuster">
      <attribute name="action">
        <value>withdraw</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <define name="ghostbuster_reply" combine="choice">
    <element name="ghostbuster">
      <attribute name="action">
        <value>withdraw</value>
      </attribute>
      <optional>
        <ref name="tag"/>
      </optional>
      <ref name="uri"/>
    </element>
  </define>
  <!-- <report_error/> element -->
  <define name="error">
    <data type="token">
      <param name="maxLength">1024</param>
    </data>
  </define>
  <define name="report_error_reply">
    <element name="report_error">
      <optional>
        <ref name="tag"/>
      </optional>
      <attribute name="error_code">
        <ref name="error"/>
      </attribute>
      <optional>
        <data type="string">
          <param name="maxLength">512000</param>
        </data>
      </optional>
    </element>
  </define>
</grammar>
<!--
  Local Variables:
  indent-tabs-mode: nil
  comment-start: "# "
  comment-start-skip: "#[ \t]*"
  End:
-->
''')

## @var router_certificate
## Parsed RelaxNG router_certificate schema
router_certificate = RelaxNGParser(r'''<?xml version="1.0" encoding="UTF-8"?>
<!--
  $Id: router-certificate-schema.rnc 5757 2014-04-05 22:42:12Z sra $
  
  RelaxNG schema for BGPSEC router certificate interchange format.
  
  At least for now, this is a trivial encapsulation of a PKCS #10
  request, a set (usually containing exactly one member) of autonomous
  system numbers, and a router-id.  Be warned that this could change
  radically by the time we have any real operational understanding of
  how these things will be used, this is just our current best guess
  to let us move forward on initial coding.
  
  Copyright (C) 2014  Dragon Research Labs ("DRL")
  
  Permission to use, copy, modify, and distribute this software for any
  purpose with or without fee is hereby granted, provided that the above
  copyright notice and this permission notice appear in all copies.
  
  THE SOFTWARE IS PROVIDED "AS IS" AND DRL DISCLAIMS ALL WARRANTIES WITH
  REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
  AND FITNESS.  IN NO EVENT SHALL DRL BE LIABLE FOR ANY SPECIAL, DIRECT,
  INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
  LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
  OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
  PERFORMANCE OF THIS SOFTWARE.
-->
<grammar ns="http://www.hactrn.net/uris/rpki/router-certificate/" xmlns="http://relaxng.org/ns/structure/1.0" datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
  <define name="version">
    <value>1</value>
  </define>
  <define name="base64">
    <data type="base64Binary">
      <param name="maxLength">512000</param>
    </data>
  </define>
  <define name="router_id">
    <data type="unsignedInt"/>
  </define>
  <define name="asn_list">
    <data type="string">
      <param name="maxLength">512000</param>
      <param name="pattern">[0-9][\-,0-9]*</param>
    </data>
  </define>
  <define name="timestamp">
    <data type="dateTime">
      <param name="pattern">.*Z</param>
    </data>
  </define>
  <!-- Core payload used in this schema. -->
  <define name="payload">
    <attribute name="router_id">
      <ref name="router_id"/>
    </attribute>
    <attribute name="asn">
      <ref name="asn_list"/>
    </attribute>
    <optional>
      <attribute name="valid_until">
        <ref name="timestamp"/>
      </attribute>
    </optional>
    <ref name="base64"/>
  </define>
  <!--
    We allow two forms, one with a wrapper to allow multiple requests in
    a single file, one without for brevity; the version attribute goes
    in the outermost element in either case.
  -->
  <start combine="choice">
    <element name="router_certificate_request">
      <attribute name="version">
        <ref name="version"/>
      </attribute>
      <ref name="payload"/>
    </element>
  </start>
  <start combine="choice">
    <element name="router_certificate_requests">
      <attribute name="version">
        <ref name="version"/>
      </attribute>
      <zeroOrMore>
        <element name="router_certificate_request">
          <ref name="payload"/>
        </element>
      </zeroOrMore>
    </element>
  </start>
</grammar>
<!--
  Local Variables:
  indent-tabs-mode: nil
  comment-start: "# "
  comment-start-skip: "#[ \t]*"
  End:
-->
''')

## @var up_down
## Parsed RelaxNG up_down schema
up_down = RelaxNGParser(r'''<?xml version="1.0" encoding="UTF-8"?>
<!--
  $Id: up-down-schema.rnc 5757 2014-04-05 22:42:12Z sra $
  
  RelaxNG schema for the up-down protocol, extracted from RFC 6492.
  
  Copyright (c) 2012 IETF Trust and the persons identified as authors
  of the code.  All rights reserved.
  
  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions
  are met:
  
  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
  
  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in
    the documentation and/or other materials provided with the
    distribution.
  
  * Neither the name of Internet Society, IETF or IETF Trust, nor the
    names of specific contributors, may be used to endorse or promote
    products derived from this software without specific prior written
    permission.
  
  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
  FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
  COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
  LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
  ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
  POSSIBILITY OF SUCH DAMAGE.
-->
<grammar ns="http://www.apnic.net/specs/rescerts/up-down/" xmlns="http://relaxng.org/ns/structure/1.0" datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
  <define name="resource_set_as">
    <data type="string">
      <param name="maxLength">512000</param>
      <param name="pattern">[\-,0-9]*</param>
    </data>
  </define>
  <define name="resource_set_ip4">
    <data type="string">
      <param name="maxLength">512000</param>
      <param name="pattern">[\-,/.0-9]*</param>
    </data>
  </define>
  <define name="resource_set_ip6">
    <data type="string">
      <param name="maxLength">512000</param>
      <param name="pattern">[\-,/:0-9a-fA-F]*</param>
    </data>
  </define>
  <define name="class_name">
    <data type="token">
      <param name="minLength">1</param>
      <param name="maxLength">1024</param>
    </data>
  </define>
  <define name="ski">
    <data type="token">
      <param name="minLength">27</param>
      <param name="maxLength">1024</param>
    </data>
  </define>
  <define name="label">
    <data type="token">
      <param name="minLength">1</param>
      <param name="maxLength">1024</param>
    </data>
  </define>
  <define name="cert_url">
    <data type="string">
      <param name="minLength">10</param>
      <param name="maxLength">4096</param>
    </data>
  </define>
  <define name="base64_binary">
    <data type="base64Binary">
      <param name="minLength">4</param>
      <param name="maxLength">512000</param>
    </data>
  </define>
  <start>
    <element name="message">
      <attribute name="version">
        <data type="positiveInteger">
          <param name="maxInclusive">1</param>
        </data>
      </attribute>
      <attribute name="sender">
        <ref name="label"/>
      </attribute>
      <attribute name="recipient">
        <ref name="label"/>
      </attribute>
      <ref name="payload"/>
    </element>
  </start>
  <define name="payload" combine="choice">
    <attribute name="type">
      <value>list</value>
    </attribute>
    <ref name="list_request"/>
  </define>
  <define name="payload" combine="choice">
    <attribute name="type">
      <value>list_response</value>
    </attribute>
    <ref name="list_response"/>
  </define>
  <define name="payload" combine="choice">
    <attribute name="type">
      <value>issue</value>
    </attribute>
    <ref name="issue_request"/>
  </define>
  <define name="payload" combine="choice">
    <attribute name="type">
      <value>issue_response</value>
    </attribute>
    <ref name="issue_response"/>
  </define>
  <define name="payload" combine="choice">
    <attribute name="type">
      <value>revoke</value>
    </attribute>
    <ref name="revoke_request"/>
  </define>
  <define name="payload" combine="choice">
    <attribute name="type">
      <value>revoke_response</value>
    </attribute>
    <ref name="revoke_response"/>
  </define>
  <define name="payload" combine="choice">
    <attribute name="type">
      <value>error_response</value>
    </attribute>
    <ref name="error_response"/>
  </define>
  <define name="list_request">
    <empty/>
  </define>
  <define name="list_response">
    <zeroOrMore>
      <ref name="class"/>
    </zeroOrMore>
  </define>
  <define name="class">
    <element name="class">
      <attribute name="class_name">
        <ref name="class_name"/>
      </attribute>
      <attribute name="cert_url">
        <ref name="cert_url"/>
      </attribute>
      <attribute name="resource_set_as">
        <ref name="resource_set_as"/>
      </attribute>
      <attribute name="resource_set_ipv4">
        <ref name="resource_set_ip4"/>
      </attribute>
      <attribute name="resource_set_ipv6">
        <ref name="resource_set_ip6"/>
      </attribute>
      <attribute name="resource_set_notafter">
        <data type="dateTime"/>
      </attribute>
      <optional>
        <attribute name="suggested_sia_head">
          <data type="anyURI">
            <param name="maxLength">1024</param>
            <param name="pattern">rsync://.+</param>
          </data>
        </attribute>
      </optional>
      <zeroOrMore>
        <element name="certificate">
          <attribute name="cert_url">
            <ref name="cert_url"/>
          </attribute>
          <optional>
            <attribute name="req_resource_set_as">
              <ref name="resource_set_as"/>
            </attribute>
          </optional>
          <optional>
            <attribute name="req_resource_set_ipv4">
              <ref name="resource_set_ip4"/>
            </attribute>
          </optional>
          <optional>
            <attribute name="req_resource_set_ipv6">
              <ref name="resource_set_ip6"/>
            </attribute>
          </optional>
          <ref name="base64_binary"/>
        </element>
      </zeroOrMore>
      <element name="issuer">
        <ref name="base64_binary"/>
      </element>
    </element>
  </define>
  <define name="issue_request">
    <element name="request">
      <attribute name="class_name">
        <ref name="class_name"/>
      </attribute>
      <optional>
        <attribute name="req_resource_set_as">
          <ref name="resource_set_as"/>
        </attribute>
      </optional>
      <optional>
        <attribute name="req_resource_set_ipv4">
          <ref name="resource_set_ip4"/>
        </attribute>
      </optional>
      <optional>
        <attribute name="req_resource_set_ipv6">
          <ref name="resource_set_ip6"/>
        </attribute>
      </optional>
      <ref name="base64_binary"/>
    </element>
  </define>
  <define name="issue_response">
    <ref name="class"/>
  </define>
  <define name="revoke_request">
    <ref name="revocation"/>
  </define>
  <define name="revoke_response">
    <ref name="revocation"/>
  </define>
  <define name="revocation">
    <element name="key">
      <attribute name="class_name">
        <ref name="class_name"/>
      </attribute>
      <attribute name="ski">
        <ref name="ski"/>
      </attribute>
    </element>
  </define>
  <define name="error_response">
    <element name="status">
      <data type="positiveInteger">
        <param name="maxInclusive">9999</param>
      </data>
    </element>
    <zeroOrMore>
      <element name="description">
        <attribute name="xml:lang">
          <data type="language"/>
        </attribute>
        <data type="string">
          <param name="maxLength">1024</param>
        </data>
      </element>
    </zeroOrMore>
  </define>
</grammar>
<!--
  Local Variables:
  indent-tabs-mode: nil
  comment-start: "# "
  comment-start-skip: "#[ \t]*"
  End:
-->
''')

del RelaxNGParser
